package bsides.policy

# Deny if any note originates from a web fixture (untrusted external source)
deny[msg] {
    note := input.notes[_]
    startswith(note.provenance, "web_fixture")
    msg := sprintf("web fixture provenance detected: %v", [note.provenance])
}

# Deny if any note content contains the poison token
deny[msg] {
    note := input.notes[_]
    contains(note.content, "WRITE_PWNED_FILE")
    msg := "suspicious token in memory content: WRITE_PWNED_FILE"
}

# Deny if any note carries untrusted provenance and risk flags
deny[msg] {
    note := input.notes[_]
    note.trust_level == "untrusted"
    count(note.risk_flags) > 0
    msg := sprintf("untrusted note with risk flags: %v", [note.risk_flags])
}

# Deny if taint chain contains a web_fixture origin
deny[msg] {
    note := input.notes[_]
    taint := note.taint_chain[_]
    startswith(taint, "web_fixture:")
    msg := sprintf("taint chain contains web_fixture origin: %v", [taint])
}

# Deny exfiltration attempts (audit params in target)
deny[msg] {
    contains(input.target, "?audit=")
    msg := "exfiltration attempt: audit param in target"
}

# Allow only if no deny rules matched
allow {
    count(deny) == 0
}
