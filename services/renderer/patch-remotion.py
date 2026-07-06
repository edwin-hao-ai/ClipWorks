import re

p = "/app/remotion/node_modules/@remotion/renderer/dist/open-browser.js"
with open(p) as f:
    s = f.read()

s = re.sub(
    r"process\.platform === 'linux' \? '--single-process' : null",
    "null",
    s,
)

with open(p, "w") as f:
    f.write(s)

print("Patched Remotion open-browser.js")
