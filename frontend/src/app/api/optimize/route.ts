import { execFile } from "node:child_process";
import path from "node:path";
import { promisify } from "node:util";
import { NextResponse } from "next/server";

import type { RiskProfile } from "@/lib/types";

export const runtime = "nodejs";

const execFileAsync = promisify(execFile);
const VALID_PROFILES = new Set<RiskProfile>([
  "Conservative",
  "Balanced",
  "Aggressive",
]);

interface OptimizeRequest {
  amount?: number;
  horizon_days?: number;
  profile?: RiskProfile;
}

export async function POST(request: Request) {
  let body: OptimizeRequest;

  try {
    body = (await request.json()) as OptimizeRequest;
  } catch {
    return NextResponse.json(
      { error: "Invalid JSON request body" },
      { status: 400 },
    );
  }

  const amount = Number(body.amount);
  const horizonDays = Number(body.horizon_days ?? 90);
  const profile = body.profile ?? "Balanced";

  if (!Number.isFinite(amount) || amount <= 0) {
    return NextResponse.json(
      { error: "amount must be a positive number" },
      { status: 400 },
    );
  }

  if (!Number.isFinite(horizonDays) || horizonDays <= 0) {
    return NextResponse.json(
      { error: "horizon_days must be a positive number" },
      { status: 400 },
    );
  }

  if (!VALID_PROFILES.has(profile)) {
    return NextResponse.json(
      { error: "profile must be Conservative, Balanced, or Aggressive" },
      { status: 400 },
    );
  }

  const repoRoot = path.resolve(process.cwd(), "..");

  try {
    const { stdout } = await execFileAsync(
      process.env.PYTHON_BIN ?? "python",
      [
        "-m",
        "src.ascend_optimizer.live_optimize",
        "--amount",
        String(amount),
        "--horizon-days",
        String(horizonDays),
        "--profile",
        profile,
        "--json",
      ],
      {
        cwd: repoRoot,
        timeout: 30_000,
        maxBuffer: 4 * 1024 * 1024,
      },
    );

    return NextResponse.json(JSON.parse(stdout));
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Optimizer execution failed";

    return NextResponse.json(
      {
        error: "Optimizer execution failed",
        detail: message,
      },
      { status: 500 },
    );
  }
}
