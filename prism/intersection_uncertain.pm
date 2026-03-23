// ================================================================
// PRISM Model: Intersection Extended (Service + Risk + Delay)
// ================================================================
// Extends intersection_base.pm with:
//   - Wait-risk buckets per direction (tracks starvation risk)
//   - Service labels (demand actively being served)
//   - Delay mode parameter (models sensing delay from Stage C)
//   - Reward structures for cumulative waiting
//
// DTMC. Each step ≈ 1 simulation second.
// ================================================================

dtmc

// ── Constants ────────────────────────────────────────────────
const int CLEARANCE_DUR = 3;

// Delay mode: 0 = normal, 1 = delayed detection active.
// Set via -const delay_mode=0 or delay_mode=1 on command line.
const int delay_mode;

// Switching probabilities conditioned on delay.
// Normal: 0.6 switch, 0.4 stay. Delayed: 0.35 switch, 0.65 stay.
const double p_switch_normal = 0.6;
const double p_switch_delayed = 0.35;
formula p_switch = (delay_mode=0 ? p_switch_normal : p_switch_delayed);

// Wait-risk escalation probability per step when demand unserved.
// Moderate->Extreme: ~1/25 per step, modeling ~25s to reach extreme.
const double p_escalate = 0.04;

// Demand arrival/departure probabilities.
const double p_veh_arrive = 0.3;
const double p_veh_depart = 0.15;
const double p_ped_arrive = 0.15;
const double p_ped_depart = 0.10;

// ── Demand model ─────────────────────────────────────────────
// Split into 4 independent modules (one per direction) to avoid
// guard overlap within a single module. Each module has exactly
// one enabled command per state, so no nondeterminism.

module DemandVehNS
    req_veh_ns : [0..1] init 0;
    [] req_veh_ns=0 -> p_veh_arrive:(req_veh_ns'=1) + (1-p_veh_arrive):(req_veh_ns'=0);
    [] req_veh_ns=1 -> p_veh_depart:(req_veh_ns'=0) + (1-p_veh_depart):(req_veh_ns'=1);
endmodule

module DemandVehEW
    req_veh_ew : [0..1] init 0;
    [] req_veh_ew=0 -> p_veh_arrive:(req_veh_ew'=1) + (1-p_veh_arrive):(req_veh_ew'=0);
    [] req_veh_ew=1 -> p_veh_depart:(req_veh_ew'=0) + (1-p_veh_depart):(req_veh_ew'=1);
endmodule

module DemandPedEW
    req_ped_ew : [0..1] init 0;
    [] req_ped_ew=0 -> p_ped_arrive:(req_ped_ew'=1) + (1-p_ped_arrive):(req_ped_ew'=0);
    [] req_ped_ew=1 -> p_ped_depart:(req_ped_ew'=0) + (1-p_ped_depart):(req_ped_ew'=1);
endmodule

module DemandPedNS
    req_ped_ns : [0..1] init 0;
    [] req_ped_ns=0 -> p_ped_arrive:(req_ped_ns'=1) + (1-p_ped_arrive):(req_ped_ns'=0);
    [] req_ped_ns=1 -> p_ped_depart:(req_ped_ns'=0) + (1-p_ped_depart):(req_ped_ns'=1);
endmodule

// ── Controller ───────────────────────────────────────────────
module Controller
    phase : [0..7] init 0;
    tip_bucket : [0..2] init 0;
    cl_count : [0..3] init 0;

    // Vehicle_NS (phase=0)
    [] phase=0 & tip_bucket=0 -> 0.7:(tip_bucket'=0) + 0.3:(tip_bucket'=1);
    [] phase=0 & tip_bucket=1 & (req_veh_ew=1 | req_ped_ew=1 | req_ped_ns=1) ->
        p_switch:(phase'=1)&(tip_bucket'=0)&(cl_count'=0) + (1-p_switch):(tip_bucket'=1);
    [] phase=0 & tip_bucket=1 & req_veh_ew=0 & req_ped_ew=0 & req_ped_ns=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=0 & tip_bucket=2 -> (phase'=1)&(tip_bucket'=0)&(cl_count'=0);

    // Clearance_after_NS (phase=1)
    [] phase=1 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=1 & cl_count=CLEARANCE_DUR -> (phase'=2)&(tip_bucket'=0)&(cl_count'=0);

    // Vehicle_EW (phase=2)
    [] phase=2 & tip_bucket=0 -> 0.7:(tip_bucket'=0) + 0.3:(tip_bucket'=1);
    [] phase=2 & tip_bucket=1 & (req_veh_ns=1 | req_ped_ew=1 | req_ped_ns=1) ->
        p_switch:(phase'=3)&(tip_bucket'=0)&(cl_count'=0) + (1-p_switch):(tip_bucket'=1);
    [] phase=2 & tip_bucket=1 & req_veh_ns=0 & req_ped_ew=0 & req_ped_ns=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=2 & tip_bucket=2 -> (phase'=3)&(tip_bucket'=0)&(cl_count'=0);

    // Clearance_after_EW (phase=3)
    [] phase=3 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=3 & cl_count=CLEARANCE_DUR -> (phase'=4)&(tip_bucket'=0)&(cl_count'=0);

    // Ped_EW (phase=4)
    [] phase=4 & tip_bucket=0 -> 0.6:(tip_bucket'=0) + 0.4:(tip_bucket'=1);
    [] phase=4 & tip_bucket=1 & (req_veh_ns=1 | req_veh_ew=1 | req_ped_ns=1) ->
        p_switch:(phase'=5)&(tip_bucket'=0)&(cl_count'=0) + (1-p_switch):(tip_bucket'=1);
    [] phase=4 & tip_bucket=1 & req_veh_ns=0 & req_veh_ew=0 & req_ped_ns=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=4 & tip_bucket=2 -> (phase'=5)&(tip_bucket'=0)&(cl_count'=0);

    // Clearance_after_Ped_EW (phase=5)
    [] phase=5 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=5 & cl_count=CLEARANCE_DUR -> (phase'=6)&(tip_bucket'=0)&(cl_count'=0);

    // Ped_NS (phase=6)
    [] phase=6 & tip_bucket=0 -> 0.6:(tip_bucket'=0) + 0.4:(tip_bucket'=1);
    [] phase=6 & tip_bucket=1 & (req_veh_ns=1 | req_veh_ew=1 | req_ped_ew=1) ->
        p_switch:(phase'=7)&(tip_bucket'=0)&(cl_count'=0) + (1-p_switch):(tip_bucket'=1);
    [] phase=6 & tip_bucket=1 & req_veh_ns=0 & req_veh_ew=0 & req_ped_ew=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=6 & tip_bucket=2 -> (phase'=7)&(tip_bucket'=0)&(cl_count'=0);

    // Clearance_after_Ped_NS (phase=7)
    [] phase=7 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=7 & cl_count=CLEARANCE_DUR -> (phase'=0)&(tip_bucket'=0)&(cl_count'=0);
endmodule

// ── Wait-risk tracker for Vehicle NS ─────────────────────────
module WaitRiskVehNS
    wr_veh_ns : [0..2] init 0;

    [] req_veh_ns=0 -> (wr_veh_ns'=0);
    [] req_veh_ns=1 & phase=0 -> (wr_veh_ns'=0);
    [] req_veh_ns=1 & phase!=0 & wr_veh_ns=0 -> (wr_veh_ns'=1);
    [] req_veh_ns=1 & phase!=0 & wr_veh_ns=1 ->
        p_escalate:(wr_veh_ns'=2) + (1-p_escalate):(wr_veh_ns'=1);
    [] req_veh_ns=1 & phase!=0 & wr_veh_ns=2 -> (wr_veh_ns'=2);
endmodule

// ── Wait-risk tracker for Ped EW ─────────────────────────────
module WaitRiskPedEW
    wr_ped_ew : [0..2] init 0;

    [] req_ped_ew=0 -> (wr_ped_ew'=0);
    [] req_ped_ew=1 & phase=4 -> (wr_ped_ew'=0);
    [] req_ped_ew=1 & phase!=4 & wr_ped_ew=0 -> (wr_ped_ew'=1);
    [] req_ped_ew=1 & phase!=4 & wr_ped_ew=1 ->
        p_escalate:(wr_ped_ew'=2) + (1-p_escalate):(wr_ped_ew'=1);
    [] req_ped_ew=1 & phase!=4 & wr_ped_ew=2 -> (wr_ped_ew'=2);
endmodule

// ── Labels ───────────────────────────────────────────────────

// Safety
label "conflict" = (phase=0 | phase=2 | phase=4 | phase=6) & cl_count > 0;

// Service: the corresponding phase is active (regardless of demand).
// This is the right definition for "this direction gets green time."
label "veh_ns_green" = phase=0;
label "ped_ew_green" = phase=4;

// Service with demand: phase is active AND demand present.
label "serve_veh_ns" = phase=0 & req_veh_ns=1;
label "serve_ped_ew" = phase=4 & req_ped_ew=1;

// Extreme wait
label "extreme_wait_veh_ns" = wr_veh_ns=2;
label "extreme_wait_ped_ew" = wr_ped_ew=2;
label "any_extreme_wait" = wr_veh_ns=2 | wr_ped_ew=2;

// ── Reward structures ────────────────────────────────────────

rewards "wait_veh_ns"
    req_veh_ns=1 & phase!=0 : 1;
endrewards

rewards "wait_ped_ew"
    req_ped_ew=1 & phase!=4 : 1;
endrewards
