/**
 * Categorisation guarantees.
 *
 * Run with: npx tsx scripts/test_categorize.mjs
 *
 * The Uber Eats case is pinned deliberately. Rule #22 "UBER EATS" already
 * outranks the broad #283 "Uber II", so priority was never the problem — #22's
 * authored pattern "Uber Eats" simply never matched the real descriptor
 * "UBER   *EATS". Normalising both sides fixes it through the existing priority
 * mechanism rather than a special case, and these assertions keep it fixed.
 */
import { resolveCategory, normalizeDescriptor } from "../src/lib/categorize.ts";
import fs from "fs";

let failures = 0;
function check(name, actual, expected) {
  const ok = actual === expected;
  if (!ok) failures++;
  console.log(`  ${ok ? "PASS" : "FAIL"}  ${name}\n        got ${JSON.stringify(actual)}, want ${JSON.stringify(expected)}`);
}

console.log("Uber Eats always maps to Meals & Entertainment:");
const eatsVariants = [
  "UBER   *EATS MASTERCARD-XXXXXX6XYIJ8-Ryan Henrich",
  "UBER *EATS HELP.UBER.C MASTERCARD-XXXXXXFXJBXL-Jackson Donahoe",
  "UBER*EATS",
  "Uber Eats",
  "uber   *eats",
  "UBER   *EATS  MASTERCARD-XXXXXXAJFANH-Mitchell Deaner",
];
for (const d of eatsVariants) {
  check(d.slice(0, 46), resolveCategory(d).subCategory, "Meals & Entertainment");
}

console.log("\nUber rides still map to Ground Transportation:");
for (const d of ["UBER   *TRIP MASTERCARD-XXXXXX1234-Someone", "UBER   * PENDING", "UBR* PENDING.UBER.COM"]) {
  check(d.slice(0, 46), resolveCategory(d).subCategory, "Ground Transportation");
}

console.log("\nNormalisation behaves:");
check("collapses spacing and asterisks", normalizeDescriptor("UBER   *EATS"), "uber eats");

// Whole-file guarantee: no Uber Eats line may land anywhere but Meals & Entertainment.
console.log("\nAcross the whole transaction import file:");
const txns = JSON.parse(fs.readFileSync("/tmp/txns.json", "utf8"));
const eats = txns.filter((t) => normalizeDescriptor(t.desc).includes("uber eats"));
const wrong = eats.filter(
  (t) => resolveCategory(t.desc, { subCategory: t.fileSub }).subCategory !== "Meals & Entertainment"
);
check(`${eats.length} Uber Eats lines, none miscategorised`, wrong.length, 0);

console.log(failures === 0 ? "\nALL CHECKS PASS" : `\n${failures} CHECK(S) FAILED`);
process.exit(failures === 0 ? 0 : 1);
