# History rewritten once before going public

As the server's checklist for making a repository public asks (arc-media-server
`docs/ALPHA-CHECKLIST.md`), the agent session links were removed from this repository's history
once, on 16 November 2026.

- A scan of every version of every file on every branch (79 commits) found no secrets, personal
  names, emails, paths or media; the only address is the example 192.168.1.20.
- `git filter-repo --message-callback` removed the `Claude-Session:` trailer from 43 commit
  messages. Every rewritten commit has the same files, author, committer and dates as before.
- References to old commit ids in the documentation were updated to the new ids.
- GitHub keeps each pull request's original commits, so a PR's Commits tab can still show the old
  messages. Local copies need re-cloning.
