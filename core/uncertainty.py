"""
Uncertainty Injection Layer
Wraps TraCI demand queries to inject delay, false requests, and detector failures.
Acts on the controller's observation/request channel — does NOT modify real world state.

Components:
  - DelayBuffer: returns demand snapshots from N steps ago
  - FalsePedInjector: adds phantom ped demand to crossing queries
  - DetectorFailure: spoofs demand values during failure windows

Usage:
    layer = UncertaintyLayer(uncertainty_config, seed=42)
    # Each simulation step:
    layer.step(current_time)
    # Demand queries route through layer instead of raw TraCI
"""

import random
from collections import deque

import traci


class DelayBuffer:
    """Delays demand observations by a fixed number of steps."""

    def __init__(self, delay_seconds, affected_lanes):
        self.delay = int(delay_seconds)
        self.affected = set(affected_lanes) if affected_lanes != "all" else None
        # Per-lane ring buffers: lane_id -> deque of past values
        self.vehicle_buffers = {}
        self.steps_applied = 0

    def is_affected(self, lane):
        return self.affected is None or lane in self.affected

    def record_and_query(self, lane, raw_value):
        """Store current raw value, return the delayed one."""
        if not self.is_affected(lane):
            return raw_value

        if lane not in self.vehicle_buffers:
            self.vehicle_buffers[lane] = deque([0] * self.delay, maxlen=self.delay + 1)

        buf = self.vehicle_buffers[lane]
        buf.append(raw_value)
        self.steps_applied += 1

        # Return oldest value in buffer (delay steps ago)
        if len(buf) > self.delay:
            return buf[0]
        return 0  # Not enough history yet — conservative default


class FalsePedInjector:
    """Injects phantom pedestrian demand at specified crossings."""

    def __init__(self, false_rate, affected_crossings, seed):
        self.false_rate = false_rate
        self.affected = set(affected_crossings)
        self.rng = random.Random(seed)
        self.injected_count = 0
        # Phantom state: crossing -> remaining steps of phantom
        self.phantom_active = {}
        self.phantom_duration = 5  # phantom persists for 5 steps once triggered

    def step(self):
        """Called each step to update phantom state."""
        # Decay active phantoms
        for crossing in list(self.phantom_active):
            self.phantom_active[crossing] -= 1
            if self.phantom_active[crossing] <= 0:
                del self.phantom_active[crossing]

        # Bernoulli trigger for new phantoms
        for crossing in self.affected:
            if crossing not in self.phantom_active:
                if self.rng.random() < self.false_rate:
                    self.phantom_active[crossing] = self.phantom_duration
                    self.injected_count += 1

    def has_phantom_at(self, wait_area):
        """Check if a phantom ped is active at this walking area."""
        return wait_area in self.phantom_active

    def get_phantom_count(self, wait_areas):
        """Return number of phantom peds across given walking areas."""
        return sum(1 for w in wait_areas if w in self.phantom_active)


class DetectorFailure:
    """Spoofs demand values for failed detectors during a failure window."""

    STUCK_OFF_VALUE = 0
    STUCK_ON_VALUE = 3  # Constant non-zero demand

    def __init__(self, mode, failure_start, failure_end, affected_lanes, seed):
        self.mode = mode  # "stuck_off" | "stuck_on" | "intermittent"
        self.start = failure_start
        self.end = failure_end
        self.affected = set(affected_lanes)
        self.rng = random.Random(seed)
        self.spoofed_steps = 0

    def is_active(self, current_time):
        return self.start <= current_time < self.end

    def spoof(self, lane, raw_value, current_time):
        """Apply failure to a single lane's demand value."""
        if not self.is_active(current_time) or lane not in self.affected:
            return raw_value

        self.spoofed_steps += 1

        if self.mode == "stuck_off":
            return self.STUCK_OFF_VALUE
        elif self.mode == "stuck_on":
            return self.STUCK_ON_VALUE
        elif self.mode == "intermittent":
            # 50% chance of returning real value, 50% stuck_off
            if self.rng.random() < 0.5:
                return raw_value
            return self.STUCK_OFF_VALUE
        return raw_value


class UncertaintyLayer:
    """
    Unified uncertainty injection layer.
    Created from a scenario's uncertainty config dict.
    """

    def __init__(self, uncertainty_config, seed=None):
        self.current_time = 0.0
        base_seed = seed if seed is not None else 0

        # C1: Delay detection
        delay_cfg = uncertainty_config.get("delay_detection", {})
        if delay_cfg.get("enabled", False):
            params = delay_cfg.get("params", {})
            self.delay = DelayBuffer(
                delay_seconds=params.get("delay_seconds", 0),
                affected_lanes=params.get("affected_lanes", "all"),
            )
        else:
            self.delay = None

        # C2: False ped request
        false_cfg = uncertainty_config.get("false_ped_request", {})
        if false_cfg.get("enabled", False) and false_cfg.get("mode") in ("random_phantom", "periodic_phantom"):
            params = false_cfg.get("params", {})
            self.false_ped = FalsePedInjector(
                false_rate=params.get("false_rate", 0.0),
                affected_crossings=params.get("affected_crossings", []),
                seed=base_seed + 1000,
            )
        else:
            self.false_ped = None

        # C3: Burst request — route_based means no runtime injection needed
        burst_cfg = uncertainty_config.get("burst_request", {})
        self.burst_route_based = (burst_cfg.get("enabled", False)
                                  and burst_cfg.get("mode") == "route_based")
        # No runtime burst injector — handled by route file

        # C4: Detector failure
        fail_cfg = uncertainty_config.get("detector_failure", {})
        if fail_cfg.get("enabled", False):
            params = fail_cfg.get("params", {})
            self.failure = DetectorFailure(
                mode=fail_cfg.get("mode", "stuck_off"),
                failure_start=params.get("failure_start", 0),
                failure_end=params.get("failure_end", 0),
                affected_lanes=params.get("affected_lanes", []),
                seed=base_seed + 2000,
            )
        else:
            self.failure = None

    def step(self, current_time):
        """Called once per simulation step to advance internal state."""
        self.current_time = current_time
        if self.false_ped:
            self.false_ped.step()

    # ── Wrapped demand queries ────────────────────────────────

    def get_vehicle_queue(self, lanes):
        """Replacement for raw get_vehicle_queue: delay + failure."""
        total = 0
        for lane in lanes:
            raw = traci.lane.getLastStepHaltingNumber(lane)
            # Apply delay
            if self.delay:
                raw = self.delay.record_and_query(lane, raw)
            # Apply failure
            if self.failure:
                raw = self.failure.spoof(lane, raw, self.current_time)
            total += raw
        return total

    def get_ped_waiting_count(self, wait_areas):
        """Replacement for raw get_ped_waiting_count: delay + false ped injection."""
        raw_count = 0
        for pid in traci.person.getIDList():
            if traci.person.getRoadID(pid) in wait_areas:
                if traci.person.getWaitingTime(pid) > 0:
                    raw_count += 1
        # Apply delay to ped count (keyed by sorted wait_areas tuple)
        if self.delay:
            area_key = "ped_" + "_".join(sorted(wait_areas))
            raw_count = self.delay.record_and_query(area_key, raw_count)
        # Add phantom peds (phantoms are NOT delayed — they represent
        # false signals injected at the current moment)
        if self.false_ped:
            raw_count += self.false_ped.get_phantom_count(wait_areas)
        return raw_count

    def has_vehicle_demand(self, lanes):
        """Replacement for raw has_vehicle_demand: delay + failure."""
        for lane in lanes:
            raw = traci.lane.getLastStepVehicleNumber(lane)
            if self.delay:
                raw = self.delay.record_and_query(f"{lane}_vn", raw)
            if self.failure:
                raw = self.failure.spoof(lane, raw, self.current_time)
            if raw > 0:
                return True
        return False

    def has_ped_demand(self, wait_areas):
        """Replacement for raw has_ped_demand: delay + false ped injection."""
        raw_count = 0
        for pid in traci.person.getIDList():
            if traci.person.getRoadID(pid) in wait_areas:
                if traci.person.getWaitingTime(pid) > 0:
                    raw_count += 1
        # Apply delay to ped presence
        if self.delay:
            area_key = "ped_has_" + "_".join(sorted(wait_areas))
            raw_count = self.delay.record_and_query(area_key, raw_count)
        if raw_count > 0:
            return True
        # Check phantoms (not delayed — injected at current moment)
        if self.false_ped:
            for w in wait_areas:
                if self.false_ped.has_phantom_at(w):
                    return True
        return False

    # ── Debug summary ─────────────────────────────────────────

    def debug_summary(self):
        """Return dict of debug counters for result output."""
        result = {}
        if self.delay:
            result["delay_applied_steps"] = self.delay.steps_applied
            result["delay_seconds"] = self.delay.delay
        if self.false_ped:
            result["false_ped_injected_count"] = self.false_ped.injected_count
        if self.failure:
            result["failure_spoofed_steps"] = self.failure.spoofed_steps
            result["failure_mode_used"] = self.failure.mode
        if self.burst_route_based:
            result["burst_mode"] = "route_based"
        return result

    def describe(self):
        """Print human-readable description of active uncertainty."""
        parts = []
        if self.delay:
            parts.append(f"delay={self.delay.delay}s")
        if self.false_ped:
            parts.append(f"false_ped(rate={self.false_ped.false_rate})")
        if self.failure:
            parts.append(f"failure({self.failure.mode}, "
                         f"t={self.failure.start}-{self.failure.end})")
        if self.burst_route_based:
            parts.append("burst=route_based")
        return ", ".join(parts) if parts else "none"
