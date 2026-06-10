export type Decision =
  | "approved"
  | "denied"
  | "escalated"
  | "store_credit"
  | "warranty_support"
  | "already_cancelled";

export type CheckStatus = "success" | "warning" | "failed";

export interface Customer {
  customer_id: string;
  name: string;
  email: string;
  tier: string;
  refund_count_90d: number;
  risk_flag: boolean;
  notes: string;
}

export interface Order {
  order_id: string;
  customer_id: string;
  product_name: string;
  category: string;
  price: number;
  delivered_days_ago: number;
  status: string;
  condition_claimed: string;
  final_sale: boolean;
  damaged_claim: boolean;
  photo_proof_available: boolean;
  payment_method: string;
  country: string;
}

export interface PolicyCheck {
  rule: string;
  passed: boolean | null;
  status: CheckStatus;
  detail: string;
}

export interface LogEntry {
  id: number;
  timestamp: string;
  session_id: string;
  step: string;
  tool_name: string;
  input_summary: string;
  output_summary: string;
  status: CheckStatus;
  decision_snapshot: string | null;
}

export type Stage =
  | "new_request"
  | "needs_clarification"
  | "waiting_for_proof"
  | "proof_received"
  | "under_manual_review"
  | "approved"
  | "denied"
  | "escalated"
  | "warranty_support"
  | "store_credit"
  | "already_cancelled";

export interface ChatResponse {
  session_id: string;
  decision: Decision;
  stage: Stage;
  pending_requirement: string;
  turn_count: number;
  message_intent?: string;
  issue_category?: string;
  response: string;
  customer: Customer | null;
  order: Order | null;
  policy_checks: PolicyCheck[];
  logs: LogEntry[];
  llm_mode: string;
}

export interface PolicyResponse {
  markdown: string;
  rules: string[];
}
