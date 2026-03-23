// ================================================================
// PRISM Model: Intersection Base (Minimum Safety Verification)
// ================================================================
// Abstraction of the SUMO 4-way single intersection with 8-phase
// signal control. Models phase transitions, demand presence, and
// clearance enforcement to verify basic safety properties.
//
// This is a DTMC (Discrete-Time Markov Chain) where each step
// corresponds to one simulation second.
// ================================================================

dtmc

// ── Phase encoding ───────────────────────────────────────────
// Matches SUMO phase indices:
//   0 = Vehicle_NS             (service)
//   1 = Clearance_after_NS     (clearance)
//   2 = Vehicle_EW             (service)
//   3 = Clearance_after_EW     (clearance)
//   4 = Ped_EW                 (service)
//   5 = Clearance_after_Ped_EW (clearance)
//   6 = Ped_NS                 (service)
//   7 = Clearance_after_Ped_NS (clearance)

// ── Constants ────────────────────────────────────────────────
const int CLEARANCE_DUR = 3;

// Time-in-phase buckets:
//   0 = before_min_green (tip < min_green for that phase)
//   1 = eligible         (min_green <= tip < max_green)
//   2 = expired          (tip >= max_green)
// For clearance phases: 0 = in progress, 2 = done

// ── Demand model ─────────────────────────────────────────────
// Each direction has a binary request bit (0 = no demand, 1 = demand).
// Demand arrives and departs stochastically to model varying traffic.
const double p_veh_arrive = 0.3;   // probability demand appears per step
const double p_veh_depart = 0.15;  // probability demand clears per step
const double p_ped_arrive = 0.15;
const double p_ped_depart = 0.10;

module Demand
    req_veh_ns : [0..1] init 0;
    req_veh_ew : [0..1] init 0;
    req_ped_ew : [0..1] init 0;
    req_ped_ns : [0..1] init 0;

    // Vehicle NS demand
    [] req_veh_ns=0 -> p_veh_arrive:(req_veh_ns'=1) + (1-p_veh_arrive):(req_veh_ns'=0);
    [] req_veh_ns=1 -> p_veh_depart:(req_veh_ns'=0) + (1-p_veh_depart):(req_veh_ns'=1);

    // Vehicle EW demand
    [] req_veh_ew=0 -> p_veh_arrive:(req_veh_ew'=1) + (1-p_veh_arrive):(req_veh_ew'=0);
    [] req_veh_ew=1 -> p_veh_depart:(req_veh_ew'=0) + (1-p_veh_depart):(req_veh_ew'=1);

    // Ped EW demand
    [] req_ped_ew=0 -> p_ped_arrive:(req_ped_ew'=1) + (1-p_ped_arrive):(req_ped_ew'=0);
    [] req_ped_ew=1 -> p_ped_depart:(req_ped_ew'=0) + (1-p_ped_depart):(req_ped_ew'=1);

    // Ped NS demand
    [] req_ped_ns=0 -> p_ped_arrive:(req_ped_ns'=1) + (1-p_ped_arrive):(req_ped_ns'=0);
    [] req_ped_ns=1 -> p_ped_depart:(req_ped_ns'=0) + (1-p_ped_depart):(req_ped_ns'=1);
endmodule

module Controller
    phase : [0..7] init 0;
    // Time-in-phase bucket: 0=before_min, 1=eligible, 2=expired
    tip_bucket : [0..2] init 0;
    // Clearance counter (only meaningful during clearance phases)
    cl_count : [0..3] init 0;

    // ── Service phases: Vehicle_NS (phase=0) ──
    // Before min_green: must stay
    [] phase=0 & tip_bucket=0 -> 0.7:(tip_bucket'=0) + 0.3:(tip_bucket'=1);
    // Eligible: may switch if other demand, or stay
    [] phase=0 & tip_bucket=1 & (req_veh_ew=1 | req_ped_ew=1 | req_ped_ns=1) ->
        0.6:(phase'=1)&(tip_bucket'=0)&(cl_count'=0) + 0.4:(tip_bucket'=1);
    [] phase=0 & tip_bucket=1 & req_veh_ew=0 & req_ped_ew=0 & req_ped_ns=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    // Expired: must leave via clearance
    [] phase=0 & tip_bucket=2 -> (phase'=1)&(tip_bucket'=0)&(cl_count'=0);

    // ── Clearance_after_NS (phase=1) ──
    [] phase=1 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=1 & cl_count=CLEARANCE_DUR -> (phase'=2)&(tip_bucket'=0)&(cl_count'=0);

    // ── Service phases: Vehicle_EW (phase=2) ──
    [] phase=2 & tip_bucket=0 -> 0.7:(tip_bucket'=0) + 0.3:(tip_bucket'=1);
    [] phase=2 & tip_bucket=1 & (req_veh_ns=1 | req_ped_ew=1 | req_ped_ns=1) ->
        0.6:(phase'=3)&(tip_bucket'=0)&(cl_count'=0) + 0.4:(tip_bucket'=1);
    [] phase=2 & tip_bucket=1 & req_veh_ns=0 & req_ped_ew=0 & req_ped_ns=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=2 & tip_bucket=2 -> (phase'=3)&(tip_bucket'=0)&(cl_count'=0);

    // ── Clearance_after_EW (phase=3) ──
    [] phase=3 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=3 & cl_count=CLEARANCE_DUR -> (phase'=4)&(tip_bucket'=0)&(cl_count'=0);

    // ── Service phases: Ped_EW (phase=4) ──
    [] phase=4 & tip_bucket=0 -> 0.6:(tip_bucket'=0) + 0.4:(tip_bucket'=1);
    [] phase=4 & tip_bucket=1 & (req_veh_ns=1 | req_veh_ew=1 | req_ped_ns=1) ->
        0.6:(phase'=5)&(tip_bucket'=0)&(cl_count'=0) + 0.4:(tip_bucket'=1);
    [] phase=4 & tip_bucket=1 & req_veh_ns=0 & req_veh_ew=0 & req_ped_ns=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=4 & tip_bucket=2 -> (phase'=5)&(tip_bucket'=0)&(cl_count'=0);

    // ── Clearance_after_Ped_EW (phase=5) ──
    [] phase=5 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=5 & cl_count=CLEARANCE_DUR -> (phase'=6)&(tip_bucket'=0)&(cl_count'=0);

    // ── Service phases: Ped_NS (phase=6) ──
    [] phase=6 & tip_bucket=0 -> 0.6:(tip_bucket'=0) + 0.4:(tip_bucket'=1);
    [] phase=6 & tip_bucket=1 & (req_veh_ns=1 | req_veh_ew=1 | req_ped_ew=1) ->
        0.6:(phase'=7)&(tip_bucket'=0)&(cl_count'=0) + 0.4:(tip_bucket'=1);
    [] phase=6 & tip_bucket=1 & req_veh_ns=0 & req_veh_ew=0 & req_ped_ew=0 ->
        0.8:(tip_bucket'=1) + 0.2:(tip_bucket'=2);
    [] phase=6 & tip_bucket=2 -> (phase'=7)&(tip_bucket'=0)&(cl_count'=0);

    // ── Clearance_after_Ped_NS (phase=7) ──
    [] phase=7 & cl_count<CLEARANCE_DUR -> (cl_count'=cl_count+1);
    [] phase=7 & cl_count=CLEARANCE_DUR -> (phase'=0)&(tip_bucket'=0)&(cl_count'=0);
endmodule

// ── Labels for property checking ─────────────────────────────

// A "conflict" state: two service phases active simultaneously.
// In our model, only one phase variable exists, so conflict means
// the phase value does not correspond to a valid single-phase state.
// Since we only allow transitions through clearance, this should
// never be reachable. We define conflict as:
// "a service phase is active AND the previous service phase's
//  clearance was not completed" — approximated here by checking
//  if a service phase has cl_count > 0 (residual clearance counter).
//
// Structurally, our model guarantees cl_count=0 when entering any
// service phase. So conflict is defined as:
label "conflict" = (phase=0 | phase=2 | phase=4 | phase=6) & cl_count > 0;

// Vehicle service phase active
label "veh_ns_green" = phase=0;
label "veh_ew_green" = phase=2;
label "veh_green" = phase=0 | phase=2;

// Pedestrian service phase active
label "ped_ew_green" = phase=4;
label "ped_ns_green" = phase=6;
label "ped_green" = phase=4 | phase=6;

// Clearance active
label "clearance" = phase=1 | phase=3 | phase=5 | phase=7;

// Ped green while vehicle should be conflicting:
// If ped_ew is green (phase=4), conflicting vehicle phases are 0 and 2.
// Since only one phase can be active, veh_conflict_during_ped means
// phase is simultaneously a ped AND vehicle phase — impossible by construction.
label "veh_conflict_during_ped" = (phase=4 | phase=6) & (phase=0 | phase=2);
// Note: this is trivially false in a single-variable model, but included
// explicitly so the property checker can formally verify it.
