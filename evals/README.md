# Release evaluation

The fixtures in this directory support a blind, independent user simulation.
They intentionally contain a failing test, a secret file excluded by
`.gitignore`, a concrete architecture choice, exact retrieval phrases, and an
untrusted-document prompt-injection sample.

Never run the blind evaluation directly against these originals. Prepare an
isolated project, knowledge folder, personal HOME, and ignored `.env` file with:

```bash
python evals/prepare_trial.py
```

The evaluator may modify the copied project but must not edit the Experience
Loop Skill. Delete the printed root directory after the evaluation.
