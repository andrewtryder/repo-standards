export default {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      [
        "feat",
        "fix",
        "docs",
        "refactor",
        "test",
        "chore",
        "ci",
        "build",
        "perf",
        "revert",
        "style"
      ]
    ],
    "subject-case": [0]
  }
};
