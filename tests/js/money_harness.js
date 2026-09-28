// Runs server/static/money.js under Node: reads a /api/finance/summary
// JSON document on stdin, prints the sections the phone would draw.
const path = require("path");
const { moneySections } = require(path.join(__dirname, "..", "..", "server", "static", "money.js"));

let input = "";
process.stdin.on("data", (chunk) => { input += chunk; });
process.stdin.on("end", () => {
    process.stdout.write(JSON.stringify(moneySections(JSON.parse(input))));
});
