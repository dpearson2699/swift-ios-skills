---
name: tabletopkit
description: "Builds multiplayer spatial board games using TabletopKit on visionOS. Use when creating tabletop game experiences with boards, pieces, cards, or dice; managing seats, turns, equipment state, TabletopAction flows, or TabletopInteraction delegates; synchronizing gameplay through FaceTime Group Activities; rendering with RealityKit; or implementing snapping, tosses, and physics on a virtual table surface."
---

# TabletopKit

Build visionOS board games whose synchronized state changes flow through `TabletopAction` and render with RealityKit. The availability matrix below owns version details.

## Contents

- [Setup](#setup)
- [Game Configuration](#game-configuration)
- [Table and Board](#table-and-board)
- [Equipment (Pieces, Cards, Dice)](#equipment-pieces-cards-dice)
- [Player Seats](#player-seats)
- [Game Actions and Turns](#game-actions-and-turns)
- [Interactions](#interactions)
- [RealityKit Rendering](#realitykit-rendering)
- [Group Activities Integration](#group-activities-integration)
- [Common Mistakes](#common-mistakes)
- [Review Checklist](#review-checklist)
- [References](#references)

## Setup

| Tier | APIs |
|---|---|
| visionOS 2.0+ | Core gameplay, equipment, seats, actions, rendering, Group Activities |
| visionOS 2.2+ | `TabletopInteraction.Configuration` |
| visionOS 26.0+ | Custom actions/state, registration, advanced toss outcomes, discarded-action observation |

Simulator supports single-player layout testing, not multiplayer.

### Project Configuration

1. `import TabletopKit` in source files that define game logic.
2. `import RealityKit` for entity-based rendering.
3. For multiplayer, add the **Group Activities** capability in Signing & Capabilities.
4. Provide table, piece, card, and dice USDZ assets in a RealityKit content bundle.

### Key Types Overview

| Type | Role |
|---|---|
| `TabletopGame` | Central game manager; owns setup, actions, observers, rendering |
| `TableSetup` | Configuration object passed to `TabletopGame` init |
| `Tabletop` / `EntityTabletop` | Protocol for the table surface |
| `Equipment` / `EntityEquipment` | Protocol for interactive game pieces |
| `TableSeat` / `EntityTableSeat` | Protocol for player seat positions |
| `TabletopAction` | Commands that modify game state |
| `TabletopInteraction` | Gesture-driven player interactions with equipment |
| `TabletopGame.Observer` | Callback protocol for reacting to confirmed actions |
| `TabletopGame.RenderDelegate` | Callback protocol for visual updates |
| `EntityRenderDelegate` | RealityKit-specific render delegate |

## Game Configuration

Build and validate a game in this order:

1. Define the tabletop, equipment, and seats.
2. Configure `TableSetup` and register every custom action type.
3. Create the game, attach its observer and renderer, claim a seat, and establish
   automatic or manual update handling.
4. Inspect the current snapshot for required equipment IDs, parents, seats, and
   counters before starting multiplayer. Fix the setup and rebuild if an
   invariant fails.

```swift
import TabletopKit
import RealityKit

let table = GameTable()
var setup = TableSetup(tabletop: table)
setup.add(seat: PlayerSeat(index: 0, pose: seatPose0))
setup.add(seat: PlayerSeat(index: 1, pose: seatPose1))
setup.add(equipment: GamePawn(id: .init(1)))
setup.add(equipment: GameDie(id: .init(2)))

let game = TabletopGame(tableSetup: setup)
game.claimAnySeat()
```

Call `update(deltaTime:)` each frame if automatic updates are not enabled via
the `.tabletopGame(_:parent:automaticUpdate:)` modifier. Read state safely with
`withCurrentSnapshot(_:)`.

## Table and Board

### Tabletop Protocol

Conform to `EntityTabletop` to define the playing surface. Provide a `shape`
(round or rectangular) and a RealityKit `Entity` for visual representation.

```swift
struct GameTable: EntityTabletop {
    var shape: TabletopShape
    var entity: Entity
    var id: EquipmentIdentifier

    init() {
        entity = try! Entity.load(named: "table/game_table", in: contentBundle)
        shape = .round(entity: entity)
        id = .init(0)
    }
}
```

### Table Shapes

Use factory methods on `TabletopShape`:

```swift
// Round table from dimensions
let round = TabletopShape.round(
    center: .init(x: 0, y: 0, z: 0),
    radius: 0.5,
    thickness: 0.05,
    in: .meters
)

// Rectangular table from entity
let rect = TabletopShape.rectangular(entity: tableEntity)
```

## Equipment (Pieces, Cards, Dice)

### Equipment Protocol

All interactive game objects conform to `Equipment` (or `EntityEquipment` for
RealityKit-rendered pieces). Each piece has an `id` (`EquipmentIdentifier`) and
an `initialState` property.

Choose the state type based on the equipment:

| State Type | Use Case |
|---|---|
| `BaseEquipmentState` | Generic pieces, pawns, tokens |
| `CardState` | Playing cards (tracks `faceUp` / face-down) |
| `DieState` | Dice with an integer `value` |
| `RawValueState` | Custom data encoded as `UInt64` |
| `CustomEquipmentState` | Custom state with a `BaseEquipmentState` plus game data; see the availability matrix |

### Defining Equipment

```swift
// Pawn -- uses BaseEquipmentState
struct GamePawn: EntityEquipment {
    var id: EquipmentIdentifier
    var initialState: BaseEquipmentState
    var entity: Entity

    init(id: EquipmentIdentifier) {
        self.id = id
        self.entity = try! Entity.load(named: "pieces/pawn", in: contentBundle)
        self.initialState = BaseEquipmentState(
            parentID: .init(0), seatControl: .any,
            pose: .identity, entity: entity
        )
    }
}

// Card -- uses CardState (tracks faceUp)
struct PlayingCard: EntityEquipment {
    var id: EquipmentIdentifier
    var initialState: CardState
    var entity: Entity

    init(id: EquipmentIdentifier) {
        self.id = id
        self.entity = try! Entity.load(named: "cards/card", in: contentBundle)
        self.initialState = .faceDown(
            parentID: .init(0), seatControl: .any,
            pose: .identity, entity: entity
        )
    }
}

// Die -- uses DieState (tracks integer value)
struct GameDie: EntityEquipment {
    var id: EquipmentIdentifier
    var initialState: DieState
    var entity: Entity

    init(id: EquipmentIdentifier) {
        self.id = id
        self.entity = try! Entity.load(named: "dice/d6", in: contentBundle)
        self.initialState = DieState(
            value: 1, parentID: .init(0), seatControl: .any,
            pose: .identity, entity: entity
        )
    }
}
```

### ControllingSeats

Restrict which players can interact with a piece via `seatControl`:
- `.any` -- any player
- `.restricted([seatID1, seatID2])` -- specific seats only
- `.restrictedCurrent([seatID1, seatID2])` -- specific seats only while they are in turn
- `.current` -- only the seat whose turn it is
- `.inherited` -- inherits from parent equipment

### Equipment Hierarchy and Layout

Equipment can be parented to other equipment. Override `layoutChildren(for:visualState:)`
to position children. Return one of:
- `.planarStacked(layout:animationDuration:)` -- cards/tiles stacked vertically
- `.planarOverlapping(layout:animationDuration:)` -- cards fanned or overlapping
- `.volumetric(layout:animationDuration:)` -- full 3D layout

See [references/tabletopkit-patterns.md](references/tabletopkit-patterns.md) for card fan, grid, and overlap layout examples.

## Player Seats

Conform to `EntityTableSeat` and provide a pose around the table:

```swift
struct PlayerSeat: EntityTableSeat {
    var id: TableSeatIdentifier
    var initialState: TableSeatState
    var entity: Entity

    init(index: Int, pose: TableVisualState.Pose2D) {
        self.id = TableSeatIdentifier(index)
        self.entity = Entity()
        self.initialState = TableSeatState(pose: pose, context: 0)
    }
}
```

Claim a seat before interacting: `game.claimAnySeat()`, `game.claimSeat(matching:)`,
or `game.releaseSeat()`. Observe changes via `TabletopGame.Observer.playerChangedSeats`.

## Game Actions and Turns

### Built-in Actions

Use `TabletopAction` factory methods to modify game state:

```swift
// Move equipment to a new parent
game.addAction(.moveEquipment(matching: pieceID, childOf: targetID, pose: newPose))

// Flip a card face-up
game.addAction(.updateEquipment(card, faceUp: true))

// Update die value
game.addAction(.updateEquipment(die, value: 6))

// Set whose turn it is
game.addAction(.setTurn(matching: TableSeatIdentifier(1)))

// Update a score counter
game.addAction(.updateCounter(matching: counterID, value: 100))

// Create a state bookmark (for undo/reset)
game.addAction(.createBookmark(id: StateBookmarkIdentifier(1)))
```

### Custom Actions

For game-specific logic, conform to `CustomAction` when the availability matrix permits it.
Custom action application and validation must depend only on the action data and
the supplied `TableState` / `TableSnapshot` so every peer resolves the same
result. Register custom action types during setup before dispatching them:

```swift
setup.register(action: CollectCoin.self)
game.addAction(CollectCoin(coinID: coinID, playerID: playerID))
```

Register each custom action type before dispatching it. See
[references/tabletopkit-patterns.md](references/tabletopkit-patterns.md)
for full custom action and custom state examples.

### Score Counters

```swift
setup.add(counter: ScoreCounter(id: .init(0), value: 0))
// Update: game.addAction(.updateCounter(matching: .init(0), value: 42))
// Read:   snapshot.counter(matching: .init(0))?.value
```

### State Bookmarks

Save and restore game state for undo/reset:

```swift
game.addAction(.createBookmark(id: StateBookmarkIdentifier(1)))
game.jumpToBookmark(matching: StateBookmarkIdentifier(1))
```

Bookmark restoration is asynchronous and network ordered. Wait for
`stateDidResetToBookmark`, then read `withCurrentSnapshot`, rebuild local UI from
that authoritative callback state, and validate the restored invariant. Do not
inspect immediately after `jumpToBookmark` or enqueue another jump on mismatch.
Load [State Bookmarks and Undo](references/tabletopkit-patterns.md#state-bookmarks-and-undo)
for the observer reconciliation pattern.

## Interactions

### TabletopInteraction.Delegate

Return an interaction delegate from the `.tabletopGame` modifier to handle
player gestures on equipment:

```swift
.tabletopGame(game.tabletopGame, parent: game.renderer.root) { value in
    if game.tabletopGame.equipment(of: GameDie.self, matching: value.startingEquipmentID) != nil {
        return DieInteraction(game: game)
    }
    return DefaultInteraction(game: game)
}
```

Use `interaction.value.gesture` for gesture-specific state. Avoid deprecated
`gesturePhase`. For destination control, prefer
`interaction.setConfiguration(.init(allowedDestinations: ...))` when available
rather than deprecated `setAllowedDestinations(_:)` or
`value.allowedDestinations`.

### Handling Gestures and Tossing Dice

Basic `toss(equipmentID:as:)` is core TabletopKit; the availability matrix owns
advanced toss outcomes.

```swift
class DieInteraction: TabletopInteraction.Delegate {
    let game: Game

    func update(interaction: TabletopInteraction) {
        switch interaction.value.phase {
        case .started:
            interaction.setConfiguration(.init(allowedDestinations: .any))
        case .update:
            if interaction.value.gesture?.phase == .ended {
                interaction.toss(
                    equipmentID: interaction.value.controlledEquipmentID,
                    as: .cube(height: 0.02, in: .meters)
                )
            }
        case .ended, .cancelled:
            break
        }
    }

    func onTossStart(interaction: TabletopInteraction,
                     outcomes: [TabletopInteraction.TossOutcome]) {
        for outcome in outcomes {
            let face = outcome.tossableRepresentation.face(for: outcome.restingOrientation)
            interaction.addAction(.updateEquipment(
                die, rawValue: face.rawValue, pose: outcome.pose
            ))
        }
    }
}
```

### Tossable Representations

Dice physics shapes: `.cube` (d6), `.tetrahedron` (d4), `.octahedron` (d8),
`.decahedron` (d10), `.dodecahedron` (d12), `.icosahedron` (d20), `.sphere`.
All take `height:in:` (or `radius:in:` for sphere) and optional `restitution:`.

### Programmatic Interactions

Start interactions from code: `game.startInteraction(onEquipmentID: pieceID)`.

See [references/tabletopkit-patterns.md](references/tabletopkit-patterns.md) for group
toss, predetermined outcomes, interaction acceptance/rejection, and destination
restriction patterns.

## RealityKit Rendering

Conform to `EntityRenderDelegate` to bridge state to RealityKit. Provide a
`root` entity. TabletopKit automatically positions `EntityEquipment` entities.

```swift
class GameRenderer: EntityRenderDelegate {
    let root = Entity()

    func onUpdate(timeInterval: Double, snapshot: TableSnapshot,
                  visualState: TableVisualState) {
        // Custom visual updates beyond automatic positioning
    }
}
```

Connect to SwiftUI with `.tabletopGame(_:parent:automaticUpdate:)` on a
`RealityView`:

```swift
struct GameView: View {
    let game: Game

    var body: some View {
        RealityView { content in
            content.entities.append(game.renderer.root)
        }
        .tabletopGame(game.tabletopGame, parent: game.renderer.root) { value in
            GameInteraction(game: game)
        }
    }
}
```

Debug outlines: `game.tabletopGame.debugDraw(options: [.drawTable, .drawSeats, .drawEquipment])`

## Group Activities Integration

TabletopKit integrates directly with GroupActivities for FaceTime-based
multiplayer. Define a `GroupActivity`, then call `coordinateWithSession(_:)`.
TabletopKit automatically synchronizes all equipment state, seat assignments,
actions, and interactions. No manual message passing required.

```swift
import GroupActivities

struct BoardGameActivity: GroupActivity {
    var metadata: GroupActivityMetadata {
        var meta = GroupActivityMetadata()
        meta.type = .generic
        meta.title = "Board Game"
        return meta
    }
}

@Observable
class GroupActivityManager {
    let tabletopGame: TabletopGame
    private var sessionTask: Task<Void, Never>?

    init(tabletopGame: TabletopGame) {
        self.tabletopGame = tabletopGame
        sessionTask = Task { @MainActor in
            for await session in BoardGameActivity.sessions() {
                tabletopGame.coordinateWithSession(session)
            }
        }
    }

    deinit { tabletopGame.detachNetworkCoordinator() }
}
```

Implement `TabletopGame.MultiplayerDelegate` for `joinAccepted()`,
`playerJoined(_:)`, `didRejectPlayer(_:reason:)`, and
`multiplayerSessionFailed(reason:)`. See
[references/tabletopkit-patterns.md](references/tabletopkit-patterns.md) for custom
network coordinators and arbiter role management.

## Common Mistakes

- **Skipping seat claim.** Players must call `claimAnySeat()` or `claimSeat(_:)`
  before interacting with equipment. Without a seat, actions are rejected.
- **Mutating state outside actions.** All state changes must go through
  `TabletopAction` or `CustomAction`. Directly modifying equipment properties
  bypasses synchronization.
- **Missing custom action registration.** Register every custom action with
  `setup.register(action:)` before use.
- **Not handling action rollback.** Actions are optimistically applied and can be
  rolled back if validation fails on the arbiter. Implement
  `actionWasRolledBack(_:snapshot:)` to revert UI state.
- **Ignoring discarded actions when available.** Implement
  `actionWasDiscarded(_:)` when local action queue pressure matters; it is
  called for local actions that cannot be enqueued.
- **Using wrong parent ID.** Equipment `parentID` in state must reference a
  valid equipment ID (typically the table or a container). An invalid parent
  causes the piece to disappear.
- **Ignoring TossOutcome faces.** After a toss, read the face from
  `outcome.tossableRepresentation.face(for: outcome.restingOrientation)` rather
  than generating a random value. The physics simulation determines the result.
- **Testing multiplayer in Simulator.** Group Activities do not work in Simulator.
  Multiplayer requires physical Apple Vision Pro devices on a FaceTime call.

## Review Checklist

- [ ] The centralized platform/availability matrix is applied
- [ ] `TableSetup` created with a `Tabletop`/`EntityTabletop` conforming type
- [ ] All equipment conforms to `Equipment` or `EntityEquipment` with correct state type
- [ ] Seats added and `claimAnySeat()` / `claimSeat(_:)` called at game start
- [ ] All custom actions registered with `setup.register(action:)`
- [ ] `TabletopGame.Observer` reconciles confirmed, rolled-back, discarded, and
      bookmark-reset outcomes with the current snapshot
- [ ] `EntityRenderDelegate` or `RenderDelegate` connected
- [ ] `.tabletopGame(_:parent:automaticUpdate:)` modifier on `RealityView`
- [ ] `GroupActivity` defined and `coordinateWithSession(_:)` called; multiplayer described as Group Activities/SharePlay synchronization
- [ ] Group Activities capability added in Xcode for multiplayer builds
- [ ] Debug visualization (`debugDraw`) disabled before release
- [ ] Device notes state Simulator is single-player only; multiplayer requires 2+ Apple Vision Pro units on FaceTime

## References

- [references/tabletopkit-patterns.md](references/tabletopkit-patterns.md) -- extended patterns for observer implementation, custom actions, dice simulation, card overlap, and network coordination
- [Apple Documentation: TabletopKit](https://sosumi.ai/documentation/tabletopkit), [Creating tabletop games](https://sosumi.ai/documentation/tabletopkit/creating-tabletop-games), [Synchronizing group gameplay](https://sosumi.ai/documentation/tabletopkit/synchronizing-group-gameplay-with-tabletopkit)
- [Simulating dice rolls](https://sosumi.ai/documentation/tabletopkit/simulating-dice-rolls-as-a-component-for-your-game), [Implementing playing card overlap](https://sosumi.ai/documentation/tabletopkit/implementing-playing-card-overlap-and-physical-characteristics)
- [WWDC24 session 10091: Build a spatial board game](https://sosumi.ai/videos/play/wwdc2024/10091/)
