# P0b-3 CausalArmor calibration — zero-call scientific freeze package

This package **does not run the calibration**. It prospectively freezes the exact environment,
population, models, scoring interpretations, and acceptance disposition before any scientific outcome.

Why this separate freeze exists: the CausalArmor paper simultaneously reports AgentDojo v1.2.2 and
629 injection/security cases. In exact AgentDojo 0.1.35, full v1.2.2 is 97 user tasks × suite-local
35 injection targets = 949 security pairs; the v1 target-ID intersection yields 629. The protocol makes
the 949 full v1.2.2 cross-product primary and reports the 629 nested subset as a sensitivity.

No network, model, GPU, vLLM, or API call is made by `P0B3_00` or `P0B3_01`.

After the author-run freeze is uploaded and independently audited, build/run the live technical preflight
and science runner against these immutable bytes. Do not edit this package after seeing outcomes.
