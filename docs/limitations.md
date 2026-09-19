# Limitations and Claim Boundaries

RouteScout intentionally preserves negative and unresolved results.

1. **Observed routed length is a proxy.** It is the cost of the available routed solution, not an
   intrinsic physical measure of net difficulty.
2. **Terminal MST is a reference, not a universal lower bound.** Multi-terminal Steiner structures
   can be shorter than terminal MST.
3. **Per-net via count is not a valid target in the current conversion.** Via-to-net attribution was
   not available and remained blocked.
4. **No GNN superiority claim.** Relational signal did not justify graph-model complexity under the
   frozen admission rule.
5. **The held-out test is consumed.** It cannot be reused for model selection or retuning.
6. **Phase 8B is a partial-reroute intervention.** It preserves non-target designer routing and
   reroutes a locked subset of eligible same-layer two-pad nets.
7. **No clear hard-first routing benefit was established.** The primary routability confidence
   interval touched zero under the preregistered decision rule.
8. **No universal autorouter claim.** Results are tied to the pinned PCBench / PCBWorld / KiCad PNS
   setup and the frozen intervention procedure.
9. **Easy/medium/hard Phase 8B strata are structural test strata.** They are not a new learned
   difficulty label.
10. **Scientific freeze beats presentation preference.** Later documentation may improve wording or
    visualization but must not rewrite frozen outcomes.
