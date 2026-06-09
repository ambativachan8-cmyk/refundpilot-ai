# RefundPilot AI — Strict Refund Policy

This is the authoritative refund policy. The agent must ground every decision in
these rules. The agent **must not invent policy exceptions** and **must log every
rule it checks**.

## Rules

1. **Standard refund window.** Refunds are allowed within **30 days** of delivery.
2. **Electronics refund window.** Electronics have a shorter window of **15 days**
   from delivery.
3. **Product condition.** A product must be **unused** to qualify, **unless** it
   was damaged on arrival.
4. **Damaged-on-arrival.** Damaged-on-arrival refunds require **photo proof**. If
   photo proof is available, the refund may be approved even if the item was used
   or the window has passed. Without photo proof, the claim is **escalated** to a
   human agent for verification.
5. **Final-sale items.** Final-sale items are **non-refundable**, with no exceptions.
6. **Refund abuse.** Customers with **more than 3 refunds in the last 90 days** are
   flagged. Their refunds are **escalated** (or denied) pending human review.
7. **Missing packages.** Missing-package claims cannot be auto-approved and are
   always **escalated**.
8. **High-value orders.** Orders above **₹25,000** require **manual approval** even
   when otherwise eligible. These are **escalated**.
9. **Gift orders.** Gift orders are refunded as **store credit**, not to the
   original payment method.
10. **Cancelled orders.** Cancelled orders were never charged/already handled and
    must **not** be refunded again. Respond with order status.
11. **Warranty issues.** Defects reported **after** the refund window are routed to
    **warranty support**, not refunded.
12. **International orders.** International orders **may require manual review** and
    are escalated when not clearly eligible.
13. **Denials.** When a refund is denied, the agent must **politely deny** and offer
    the best available alternative (e.g., warranty, store credit, escalation).
14. **No invented exceptions.** The agent must never fabricate an exception that is
    not written in this policy.
15. **Auditability.** Every rule the agent checks must be recorded in the reasoning
    log with a pass / warning / fail status.

## Decision precedence (highest first)

1. Cancelled order → `already_cancelled`
2. Final-sale item → `denied`
3. Missing package → `escalated`
4. Refund abuse (>3 in 90d) → `escalated`
5. Damaged on arrival
   - with photo proof → `approved`
   - without photo proof → `escalated`
6. Outside refund window
   - defect / warranty context → `warranty_support`
   - otherwise → `denied`
7. Product used (and not damaged) → `denied`
8. High-value (> ₹25,000) → `escalated`
9. Gift order → `store_credit`
10. International order (not clearly eligible) → `escalated`
11. Otherwise → `approved`
