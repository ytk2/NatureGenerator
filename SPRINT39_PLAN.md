# Sprint 39 Plan — TPMS Domain Sizing Modes

## Status

Implementation and manual Autodesk Fusion acceptance are complete.

## Goal

Add a second, period-aligned way to size the independent TPMS Volume
rectangular domain without changing released Dimensions behavior.

## Scope

- add metadata-driven Dimensions and Cell Count domain modes
- retain Dimensions as the default
- resolve Cell Count dimensions through `cells × Period`
- keep the rectangular domain centered at the origin
- preserve separate in-command values for both sizing modes
- show effective cells or calculated dimensions as read-only diagnostics
- carry requested and resolved domain provenance through cost and result data
- preserve all Sprint 38 geometry, Preview Quality, safety, and lifecycle paths

## Exclusions

- arbitrary selected-body clipping
- Samples per Cell or automatic resolution selection
- resampling to force node-aligned opposing boundaries
- background work, caching, threads, async execution, or event-loop pumping
- BRep conversion, remeshing, or decimation

## Definition of done

- one Fusion-independent resolver owns all physical-dimension decisions
- downstream sampling and closure use only resolved dimensions
- Dimensions mode retains every existing canonical digest
- Cell Count supports all TPMS, geometry, boundary, and Preview Quality choices
- both UI parameter banks survive repeated mode changes
- oversized calculated dimensions fail before scalar allocation
- focused and full warnings-as-errors validation pass
- documentation records period alignment versus sample-node alignment
- changes remain uncommitted and unpushed for review
