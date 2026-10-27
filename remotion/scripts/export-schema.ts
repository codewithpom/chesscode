// Writes spec/video_spec.schema.json from the Zod contract. `--check` fails if the file is stale (CI).
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import { z } from "zod";
import { VideoSpec } from "../src/spec/schema";

const out = resolve(__dirname, "../../spec/video_spec.schema.json");
const json =
  JSON.stringify(z.toJSONSchema(VideoSpec, { target: "draft-2020-12", io: "input" }), null, 2) + "\n";

if (process.argv.includes("--check")) {
  if (!existsSync(out) || readFileSync(out, "utf8") !== json) {
    console.error("spec/video_spec.schema.json is stale: run `npm run export-schema`");
    process.exit(1);
  }
} else {
  writeFileSync(out, json);
  console.log(`wrote ${out}`);
}
