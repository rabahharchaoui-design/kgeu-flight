#!/bin/zsh
# Pocket Flight Sim bug tickets (the private repo rabahharchaoui-design/pocketsim-bugs).
# The token lives in ~/.pocketsim-bugs-token (Issues read and write only, mode 600); it is never printed.
#   tools/bugs.sh                 open issues: number, labels, title, created
#   tools/bugs.sh show <n>        one issue in full (title, labels, state, body, comments)
#   tools/bugs.sh close <n> "<comment>"   comment, then close (the game reads "Fixed in <version>" from the comment)
#   tools/bugs.sh json            the open issues as raw JSON (for scripts)
set -e
REPO=rabahharchaoui-design/pocketsim-bugs
TOK_FILE=${POCKETSIM_BUGS_TOKEN_FILE:-$HOME/.pocketsim-bugs-token}
[[ -r $TOK_FILE ]] || { echo "no token file at $TOK_FILE" >&2; exit 2; }
TOK=$(tr -d '\n\r ' < "$TOK_FILE")
api() {   # method path [json body]
  local m=$1 p=$2 b=$3
  local -a extra; extra=()
  [[ -n $b ]] && extra=(-H "Content-Type: application/json" --data-binary "$b")
  curl -sS -X "$m" -H "Authorization: Bearer $TOK" -H "Accept: application/vnd.github+json" -H "X-GitHub-Api-Version: 2022-11-28" \
    "${extra[@]}" "https://api.github.com/repos/$REPO$p"
}
py() { J="$1" python3 -c "import json,os,sys; d=json.loads(os.environ['J'])
$2"; }
cmd=${1:-list}
case $cmd in
  list)
    py "$(api GET '/issues?state=open&per_page=100&sort=created&direction=asc')" '
if isinstance(d,dict): print("error:",d.get("message")); sys.exit(1)
d=[i for i in d if "pull_request" not in i]
if not d: print("no open issues"); sys.exit(0)
for i in d:
    labels=",".join(l["name"] for l in i.get("labels",[])) or "-"
    print("#%-5s %-22s %s  %s" % (i["number"], labels, i["created_at"][:10], i["title"]))' ;;
  json)
    api GET '/issues?state=open&per_page=100&sort=created&direction=asc' ;;
  show)
    n=$2; [[ -n $n ]] || { echo "usage: tools/bugs.sh show <n>" >&2; exit 2; }
    py "$(api GET "/issues/$n")" '
if "number" not in d: print("error:",d.get("message")); sys.exit(1)
print("#%s  %s" % (d["number"], d["title"]))
print("state:",d["state"],"  labels:",", ".join(l["name"] for l in d.get("labels",[])) or "-","  created:",d["created_at"],"  url:",d["html_url"])
print(); print(d.get("body") or "(no body)")'
    echo; echo "--- comments"
    py "$(api GET "/issues/$n/comments?per_page=100")" '
for c in d: print("[%s] %s: %s" % (c["created_at"][:16], c["user"]["login"], c["body"]))' ;;
  close)
    n=$2; msg=$3; [[ -n $n && -n $msg ]] || { echo "usage: tools/bugs.sh close <n> \"<comment>\"" >&2; exit 2; }
    body=$(M="$msg" python3 -c 'import json,os; print(json.dumps({"body":os.environ["M"]}))')
    py "$(api POST "/issues/$n/comments" "$body")" 'print("comment", d.get("id") or d.get("message"))'
    py "$(api PATCH "/issues/$n" '{"state":"closed","state_reason":"completed"}')" 'print("issue #%s %s" % (d.get("number"), d.get("state") or d.get("message")))' ;;
  *) echo "usage: tools/bugs.sh [list|json|show <n>|close <n> \"<comment>\"]" >&2; exit 2 ;;
esac
