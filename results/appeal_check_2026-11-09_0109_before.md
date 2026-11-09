# Appeal check, criterion 4 (before)

- Produced by: `run_appeals.py::main`
- Target: 5 of 5 real appeals pass, 3 of 3 fake ids return 404 and leave no trace

| Trial | Real appeals passing | Fake ids passing |
|---|---|---|
| 1 | 5/5 | 3/3 |
| 2 | 5/5 | 3/3 |
| 3 | 5/5 | 3/3 |

## Raw results, trial 1

```json
[
  {
    "kind": "real",
    "content_id": "c6d639d79ebd",
    "appeal_status": 200,
    "appeal_response": {
      "content_id": "c6d639d79ebd",
      "message": "Thanks. Your appeal is recorded and this piece is now marked as under review. The original label stays on file, and a person will look at it with your reasoning.",
      "original_guess": "unsure",
      "original_label": "We can't tell whether this was written by a person or with help from AI, so we are not making a call either way. This is not an accusation. Our check is easily thrown off by short, plain, or very formal writing. If you wrote this, you don't need to do anything.",
      "status": "under_review"
    },
    "content_status": "under_review",
    "appeal_log_entries": 1,
    "pass": true
  },
  {
    "kind": "real",
    "content_id": "2061e3c416cc",
    "appeal_status": 200,
    "appeal_response": {
      "content_id": "2061e3c416cc",
      "message": "Thanks. Your appeal is recorded and this piece is now marked as under review. The original label stays on file, and a person will look at it with your reasoning.",
      "original_guess": "human",
      "original_label": "We think a person most likely wrote this. Our check found the variety in sentences and word choice that we usually see in human writing.",
      "status": "under_review"
    },
    "content_status": "under_review",
    "appeal_log_entries": 1,
    "pass": true
  },
  {
    "kind": "real",
    "content_id": "5266d4803edb",
    "appeal_status": 200,
    "appeal_response": {
      "content_id": "5266d4803edb",
      "message": "Thanks. Your appeal is recorded and this piece is now marked as under review. The original label stays on file, and a person will look at it with your reasoning.",
      "original_guess": "unsure",
      "original_label": "We can't tell whether this was written by a person or with help from AI, so we are not making a call either way. This is not an accusation. Our check is easily thrown off by short, plain, or very formal writing. If you wrote this, you don't need to do anything.",
      "status": "under_review"
    },
    "content_status": "under_review",
    "appeal_log_entries": 1,
    "pass": true
  },
  {
    "kind": "real",
    "content_id": "483455b4d6f1",
    "appeal_status": 200,
    "appeal_response": {
      "content_id": "483455b4d6f1",
      "message": "Thanks. Your appeal is recorded and this piece is now marked as under review. The original label stays on file, and a person will look at it with your reasoning.",
      "original_guess": "unsure",
      "original_label": "We can't tell whether this was written by a person or with help from AI, so we are not making a call either way. This is not an accusation. Our check is easily thrown off by short, plain, or very formal writing. If you wrote this, you don't need to do anything.",
      "status": "under_review"
    },
    "content_status": "under_review",
    "appeal_log_entries": 1,
    "pass": true
  },
  {
    "kind": "real",
    "content_id": "943a224c33b0",
    "appeal_status": 200,
    "appeal_response": {
      "content_id": "943a224c33b0",
      "message": "Thanks. Your appeal is recorded and this piece is now marked as under review. The original label stays on file, and a person will look at it with your reasoning.",
      "original_guess": "unsure",
      "original_label": "We can't tell whether this was written by a person or with help from AI, so we are not making a call either way. This is not an accusation. Our check is easily thrown off by short, plain, or very formal writing. If you wrote this, you don't need to do anything.",
      "status": "under_review"
    },
    "content_status": "under_review",
    "appeal_log_entries": 1,
    "pass": true
  },
  {
    "kind": "fake",
    "content_id": "c79c5ca9daa0",
    "appeal_status": 404,
    "appeal_response": {
      "error": "not_found",
      "message": "No submission with content_id 'c79c5ca9daa0'."
    },
    "log_entries_with_id": 0,
    "pass": true
  },
  {
    "kind": "fake",
    "content_id": "5aee69b1c6c6",
    "appeal_status": 404,
    "appeal_response": {
      "error": "not_found",
      "message": "No submission with content_id '5aee69b1c6c6'."
    },
    "log_entries_with_id": 0,
    "pass": true
  },
  {
    "kind": "fake",
    "content_id": "78c823719f21",
    "appeal_status": 404,
    "appeal_response": {
      "error": "not_found",
      "message": "No submission with content_id '78c823719f21'."
    },
    "log_entries_with_id": 0,
    "pass": true
  }
]
```
