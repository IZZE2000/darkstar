# Product Guidelines

## Communication Tone
- **Hybrid Technical-Approachable**: The language should be accessible to homeowners while remaining grounded in engineering reality. Use helpful explanations for complex concepts, but do not shy away from "real" technical terms like MILP (Mixed-Integer Linear Programming) or SoC (State of Charge).
- **Professional & Precise**: Maintain a tone that is minimalist and direct, ensuring clarity over verbosity.

## Visual Design Principles
- **Visual Hierarchy**: Prioritize high-level health status and optimization outcomes. Secondary metrics should be available but deprioritized to prevent clutter.
- **Brand Aesthetic**: Maintain the "Darkstar" identity with a focus on dark-mode native design and professional data presentation.

## Error Handling & Safety
- **Safe Fail-Over**: When critical errors occur, the system must prioritize safety by falling back to a "Graceful Degradation" mode (e.g., standard battery passthrough).
- **Clear Guidance**: Communication of errors should mix technical context with user-centric resolution steps, explaining *what* happened and *how* the user can fix it within the UI.

## Onboarding & Configuration
- **Smart Discovery**: Maximize automated detection of the environment (e.g., Home Assistant integration) to reduce manual entry.
- **Interactive Setup**: Use guided walkthroughs to help users map sensors and understand core energy concepts during the initial configuration.

## Development & Release Philosophy
- **"Fail Fast" Beta**: While in the public beta phase, prioritize rapid iteration and feature delivery.
- **Staged Rollouts**: Utilize the `darkstar-dev` version for rigorous testing by early adopters before promoting changes to the stable release channel.
