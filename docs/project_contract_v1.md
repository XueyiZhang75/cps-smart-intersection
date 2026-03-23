# Project Contract v1

## 1. Project Scope
- Project title: Safe and Robust Smart Intersection Control under Sensing Uncertainty and Abnormal Requests
- System scope: single four-way intersection
- Focus: safe, robust, interpretable control under uncertain sensing and abnormal requests
- Main platforms: SUMO + Python/TraCI + PRISM

## 2. Core Phase Set
- P0: Vehicle_NS
- P1: Clearance_after_NS
- P2: Vehicle_EW
- P3: Clearance_after_EW
- P4: Ped_EW
- P5: Clearance_after_Ped_EW
- P6: Ped_NS
- P7: Clearance_after_Ped_NS

## 3. Initial Timing Parameters
- Simulation step: 1 s
- Control decision period: 5 s
- Minimum green: 15 s
- Yellow time: 3 s
- All-red time: 2 s
- Minimum switch interval: 8 s
- Debounce window: 5 s

## 4. Controllers to Implement
- Fixed-Time
- Actuated
- Adaptive-Only
- Adaptive + Safety Shield

## 5. Core Uncertainty Types
- Delayed vehicle detection
- False pedestrian requests
- Bursty requests
- Partial detector failure

## 6. Core Evaluation Dimensions
- Safety compliance
- Service guarantee
- Efficiency
- Switching stability

## 7. Immediate Engineering Goal
Build a minimal runnable SUMO four-way intersection with:
- vehicle flows
- pedestrian crossings
- configurable traffic-light phases
- fixed-time signal cycle

## 8. File Layout
- docs/: design notes and specifications
- sumo/net/: network files
- sumo/routes/: route files
- sumo/cfg/: SUMO config files
- sumo/detectors/: detector config files
- sumo/outputs/: simulation raw outputs
- controllers/: Python controller code
- prism/: PRISM models and properties
- logs/: experiment logs
- results/: processed results
- figures/: plots and screenshots