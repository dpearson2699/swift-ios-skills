# TabletopKit Extended Patterns

Overflow reference for the `tabletopkit` skill. Contains advanced patterns for
observer implementation, custom actions, dice physics, card layouts, network
coordination, and full game architecture examples.

Availability notes:
- Core TabletopKit APIs are visionOS 2.0+.
- `TabletopInteraction.Configuration` is visionOS 2.2+.
- `CustomAction`, `CustomEquipmentState`, `TableSetup.register(action:)`, and
  direct custom-action dispatch are visionOS 26.0+.
- Apple's dice, card-overlap, and group-gameplay sample projects referenced by
  these patterns use visionOS 26.0+ / Xcode 26.0+ APIs.

## Contents

- [Observer Patterns](#observer-patterns)
- [Custom Action Patterns](#custom-action-patterns)
- [Dice Simulation](#dice-simulation)
- [Card and Tile Layouts](#card-and-tile-layouts)
- [Interaction Delegate Patterns](#interaction-delegate-patterns)
- [Full Game Architecture](#full-game-architecture)
- [Network and Multiplayer Coordination](#network-and-multiplayer-coordination)
- [State Bookmarks and Undo](#state-bookmarks-and-undo)
- [Score Tracking](#score-tracking)
- [Debugging Techniques](#debugging-techniques)

## Observer Patterns

### Implementing TabletopGame.Observer

The observer receives callbacks when actions are validated, pending, confirmed,
rolled back, discarded, or cancelled. Use `actionWasConfirmed` as the primary
hook for updating game-specific state.

```swift
import TabletopKit

class GameObserver: TabletopGame.Observer {
    weak var game: Game?

    func validateAction(_ action: some TabletopAction,
                        snapshot: TableSnapshot) -> Bool {
        // Return false to reject the action before it applies.
        // Called on the arbiter (host) device in multiplayer.
        if let moveAction = action as? MoveEquipmentAction {
            // Validate move is legal in current game rules
            return isLegalMove(moveAction, in: snapshot)
        }
        return true
    }

    func actionIsPending(_ action: some TabletopAction,
                         oldSnapshot: TableSnapshot,
                         newSnapshot: TableSnapshot) {
        // Action applied locally but not yet confirmed by arbiter.
        // Use for optimistic UI updates.
    }

    func actionWasConfirmed(_ action: some TabletopAction,
                            oldSnapshot: TableSnapshot,
                            newSnapshot: TableSnapshot) {
        guard let game else { return }

        // Handle built-in actions
        if let setTurn = action as? SetTurnAction {
            game.currentTurnSeats = setTurn.seatIDsInTurn
            return
        }

        if let counterAction = action as? UpdateCounterAction {
            game.scores[counterAction.counterID] = counterAction.newValue
            return
        }

        // Handle custom actions
        if let collect = CollectCoin(from: action) {
            handleCoinCollected(collect, snapshot: newSnapshot)
            return
        }
    }

    func actionWasRolledBack(_ action: some TabletopAction,
                             snapshot: TableSnapshot) {
        // Arbiter rejected the action. Revert optimistic UI.
    }

    func actionWasDiscarded(_ action: some TabletopAction) {
        // visionOS 26.0+: local action could not be enqueued.
        // Reconcile UI that expected the action to become pending.
    }

    func actionWasCancelled(_ action: some TabletopAction,
                            reason: TabletopGame.ActionCancellationReason) {
        switch reason {
        case .actionInvalidated:
            // Action was invalidated by a conflicting action
            break
        case .interactionCancelled:
            // The interaction that queued this action was cancelled
            break
        @unknown default:
            break
        }
    }

    func playerChangedSeats(_ player: Player,
                            oldSeat: (any TableSeat)?,
                            newSeat: (any TableSeat)?,
                            snapshot: TableSnapshot) {
        game?.updatePlayerList(snapshot: snapshot)
    }

    func stateDidResetToBookmark(_ bookmarkID: StateBookmarkIdentifier) {
        game?.handleStateReset()
    }

    private func isLegalMove(_ action: MoveEquipmentAction,
                             in snapshot: TableSnapshot) -> Bool {
        // Game-specific validation
        true
    }

    private func handleCoinCollected(_ action: CollectCoin,
                                     snapshot: TableSnapshot) {
        // Update game-specific state
    }
}
```

### Registering and Removing Observers

```swift
let observer = GameObserver()
observer.game = self
game.addObserver(observer)

// Later, when done:
game.removeObserver(observer)
```

## Custom Action Patterns

`CustomAction` and `CustomEquipmentState` are visionOS 26.0+. Register each
custom action type with `TableSetup.register(action:)` before dispatching it.
Keep `validate(snapshot:)` and `apply(table:)` deterministic: they should use
only the supplied snapshot/table state and the data stored in the action.

### Defining a Custom Action

Custom actions modify `TableState` directly and support validation. TabletopKit
syncs the resulting actions across the network.

```swift
struct FlipAllCards: CustomAction {
    let targetFaceUp: Bool

    init?(from action: some TabletopAction) {
        // Decode from the generic action's context
        let raw = action.context
        self.targetFaceUp = (raw & 1) == 1
    }

    func validate(snapshot: TableSnapshot) -> Bool {
        // Ensure there are cards to flip
        let cards = snapshot.equipment(of: PlayingCard.self)
        return !cards.isEmpty
    }

    func apply(table: inout TableState) {
        let cardIDs = table.equipment.ids(of: PlayingCard.self)
        for cardID in cardIDs {
            if var cardState = table.equipment.state[of: PlayingCard.self, id: cardID] {
                cardState.faceUp = targetFaceUp
                table.equipment.state[of: PlayingCard.self, id: cardID] = cardState
            }
        }
    }
}
```

### Dispatching Custom Actions

```swift
// Register during setup
setup.register(action: FlipAllCards.self)

// Dispatch during gameplay
let flipAction = TabletopAction.customAction(
    FlipAllCards(targetFaceUp: true),
    context: 1  // encode targetFaceUp as context
)
game.addAction(flipAction)
```

### Custom Action with Equipment State Mutation

For actions that modify equipment with `CustomEquipmentState` (visionOS 26.0+):

```swift
struct PlayerState: CustomEquipmentState {
    var base: BaseEquipmentState
    var health: Int
    var coinsCount: Int
}

struct DecrementHealth: CustomAction {
    let playerID: EquipmentIdentifier

    init?(from action: some TabletopAction) {
        guard let moveAction = action as? UpdateEquipmentAction else { return nil }
        self.playerID = moveAction.equipmentID
    }

    func validate(snapshot: TableSnapshot) -> Bool {
        guard let (_, state) = snapshot.equipment(
            of: PlayerPiece.self, matching: playerID
        ) else { return false }
        return state.health > 0
    }

    func apply(table: inout TableState) {
        if var state = table.equipment.state[of: PlayerPiece.self, id: playerID] {
            state.health = max(0, state.health - 1)
            table.equipment.state[of: PlayerPiece.self, id: playerID] = state
        }
    }
}
```

## Dice Simulation

These dice patterns follow Apple's visionOS 26.0+ dice sample. The underlying
`TossableRepresentation`, toss interaction, and `RawValueState` APIs are part of
TabletopKit. `onTossStart(interaction:outcomes:)`,
`TabletopInteraction.TossOutcome`, and `TossableRepresentation.face(for:)` are
visionOS 26.0+; gate them before back-deploying.

### Tossable Representations and Face Mapping

Each die shape has a corresponding face type for mapping physical orientations
to game values.

```swift
// Standard 6-sided die
let d6 = TossableRepresentation.cube(height: 0.02, in: .meters)

// Map cube faces to values
let cubeFaceValues: [TossableRepresentation.CubeFace: Int] = [
    .a: 1, .b: 2, .c: 3,
    .d: 4, .e: 5, .f: 6
]
```

### Implementing Dice Toss in an Interaction Delegate

```swift
class DiceInteraction: TabletopInteraction.Delegate {
    let game: Game
    let die: GameDie
    let tossableRep: TossableRepresentation

    init(game: Game, die: GameDie) {
        self.game = game
        self.die = die
        self.tossableRep = .cube(height: 0.02, in: .meters)
    }

    func update(interaction: TabletopInteraction) {
        guard let gesture = interaction.value.gesture else { return }

        switch gesture.phase {
        case .started:
            break
        case .update:
            break
        case .ended:
            // Player released -- initiate toss
            interaction.toss(
                equipmentID: die.id,
                as: tossableRep
            )
        case .cancelled:
            interaction.cancel()
        @unknown default:
            break
        }
    }

    func onTossStart(interaction: TabletopInteraction,
                     outcomes: [TabletopInteraction.TossOutcome]) {
        for outcome in outcomes {
            guard outcome.id == die.id else { continue }

            // Physics simulation determines final face
            let face = outcome.tossableRepresentation.face(
                for: outcome.restingOrientation
            )

            interaction.addAction(.updateEquipment(
                die,
                rawValue: face.rawValue,
                pose: outcome.pose
            ))
        }
    }
}
```

### Predetermined Outcomes

Override the physics result for scripted gameplay:

```swift
func onTossStart(interaction: TabletopInteraction,
                 outcomes: [TabletopInteraction.TossOutcome]) {
    for outcome in outcomes {
        // Force the highest-scoring face instead of physics result
        let bestFace = TossableRepresentation.CubeFace.f  // value 6
        interaction.addAction(.updateEquipment(
            die,
            rawValue: bestFace.rawValue,
            pose: outcome.pose
        ))
    }
}
```

### Group Toss (Multiple Dice)

Move extra dice under the controlled die, then toss all together:

```swift
func update(interaction: TabletopInteraction) {
    switch interaction.value.phase {
    case .started:
        // Group dice under the controlled die
        for (index, extraDie) in otherDice.enumerated() {
            interaction.addAction(.moveEquipment(
                extraDie,
                childOf: controlledDie,
                pose: hexagonPoses[index]
            ))
        }

    case .update:
        if interaction.value.gesture?.phase == .ended {
            // Toss all dice
            interaction.toss(equipmentID: controlledDie.id,
                             as: controlledDie.tossableRepresentation)
            for die in otherDice {
                interaction.toss(equipmentID: die.id,
                                 as: die.tossableRepresentation)
            }
        }

    case .ended:
        // Calculate total score
        game.updateScore(for: [controlledDie] + otherDice)

    default: break
    }
}
```

### Reading Die Score After Toss

```swift
func updateScore(for dice: [GameDie]) {
    tabletopGame.withCurrentSnapshot { snapshot in
        var total = 0
        for die in dice {
            let state: RawValueState = snapshot.state(for: die)
            let face = die.tossableRepresentation.face(for:
                Rotation3D(/* from state */))
            total += die.faceMap[face] ?? 0
        }
        lastRollScore = total
    }
}
```

## Card and Tile Layouts

The planar layout APIs are visionOS 2.0+. Apple's advanced physical card
overlap sample uses visionOS 26.0+ / Xcode 26.0+ material.

### Stacked Card Layout

Use `planarStacked` for neat card piles:

```swift
func layoutChildren(for snapshot: TableSnapshot,
                    visualState: TableVisualState) -> any EquipmentLayout {
    let childIDs = snapshot.equipmentIDs(childrenOf: id)
    let poses = childIDs.enumerated().map { index, childID in
        EquipmentPose2D(id: childID, pose: .init(
            position: .init(x: 0, z: 0),
            rotation: .zero
        ))
    }
    return EquipmentLayout.planarStacked(
        layout: poses,
        animationDuration: 0.25
    )
}
```

### Fan / Hand Layout

Fan cards in an arc for a player's hand:

```swift
func layoutChildren(for snapshot: TableSnapshot,
                    visualState: TableVisualState) -> any EquipmentLayout {
    let childIDs = snapshot.equipmentIDs(childrenOf: id)
    let count = childIDs.count
    let fanAngle = Angle2D(degrees: 30)
    let spacing = 0.04

    let poses = childIDs.enumerated().map { index, childID in
        let fraction = count > 1
            ? Double(index) / Double(count - 1) - 0.5
            : 0
        let angle = Angle2D(radians: fanAngle.radians * fraction)
        let x = spacing * fraction * Double(count)

        return EquipmentPose2D(id: childID, pose: .init(
            position: .init(x: x, z: 0),
            rotation: angle
        ))
    }
    return EquipmentLayout.planarOverlapping(
        layout: poses,
        animationDuration: 0.3
    )
}
```

### Grid Layout for Tiles

```swift
func layoutChildren(for snapshot: TableSnapshot,
                    visualState: TableVisualState) -> any EquipmentLayout {
    let childIDs = snapshot.equipmentIDs(childrenOf: id)
    let columns = 4
    let tileSize = 0.06

    let poses = childIDs.enumerated().map { index, childID in
        let row = index / columns
        let col = index % columns
        return EquipmentPose2D(id: childID, pose: .init(
            position: .init(
                x: Double(col) * tileSize,
                z: Double(row) * tileSize
            ),
            rotation: .zero
        ))
    }
    return EquipmentLayout.planarStacked(
        layout: poses,
        animationDuration: 0.2
    )
}
```

## Interaction Delegate Patterns

Use `interaction.value.gesture` for gesture-specific state. Avoid deprecated
`gesturePhase`. Use `interaction.setConfiguration(_:)` with
`TabletopInteraction.Configuration` on visionOS 2.2+ instead of deprecated
`setAllowedDestinations(_:)` or `value.allowedDestinations`.

### Accepting and Rejecting Interactions

Control which interactions the game allows:

```swift
func shouldAcceptInteraction(
    initialValue: TabletopInteraction.Value,
    handoffValue: TabletopInteraction.Value?
) -> TabletopInteraction.NewInteractionIntent {
    // Only allow interaction if it is this player's turn
    guard isCurrentPlayersTurn(initialValue.playerID) else {
        return .reject
    }
    return .acceptWithConfiguration(.init(allowedDestinations: .any))
}
```

### Direct vs. Indirect Interaction

```swift
func shouldAcceptDirectInteraction(
    initialValue: TabletopInteraction.Value,
    handoffValue: TabletopInteraction.Value?
) -> TabletopInteraction.NewDirectInteractionIntent {
    .accept(
        configuration: .init(allowedDestinations: .any),
        constants: .init(pickupBehavior: .default)
    )
}

func shouldAcceptIndirectInteraction(
    initialValue: TabletopInteraction.Value,
    handoffValue: TabletopInteraction.Value?
) -> TabletopInteraction.NewIndirectInteractionIntent {
    .accept(
        configuration: .init(allowedDestinations: .any),
        constants: .init(rotationAlignment: .automatic)
    )
}
```

### Restricting Destinations

```swift
// Allow dropping only on specific equipment
interaction.setConfiguration(.init(
    allowedDestinations: .restricted([
        EquipmentIdentifier(10),
        EquipmentIdentifier(11),
        EquipmentIdentifier(12)
    ])
))
```

### Moving Equipment on Interaction End

```swift
func update(interaction: TabletopInteraction) {
    if interaction.value.phase == .ended,
       let destination = interaction.value.proposedDestination {
        interaction.addAction(.moveEquipment(
            matching: interaction.value.controlledEquipmentID,
            childOf: destination.equipmentID,
            pose: destination.pose
        ))
    }
}
```

## Full Game Architecture

### Recommended Structure

```
Game/
  Game.swift              -- TabletopGame owner, game lifecycle
  GameSetup.swift         -- TableSetup configuration, equipment creation
  GameObserver.swift      -- TabletopGame.Observer implementation
  GameRenderer.swift      -- EntityRenderDelegate implementation
  GameView.swift          -- SwiftUI RealityView + .tabletopGame modifier
  Equipment/
    Board.swift           -- EntityTabletop conformance
    Pawn.swift            -- EntityEquipment (BaseEquipmentState)
    Card.swift            -- EntityEquipment (CardState)
    Die.swift             -- EntityEquipment (DieState or RawValueState)
    CardPile.swift        -- Equipment group with layoutChildren
  Interactions/
    PawnInteraction.swift
    CardInteraction.swift
    DieInteraction.swift
  Actions/
    CustomActions.swift   -- CustomAction conformances
  Multiplayer/
    Activity.swift        -- GroupActivity definition
    GroupActivityManager.swift
```

### Game Class Skeleton

```swift
import TabletopKit
import RealityKit

@Observable
class Game {
    let tabletopGame: TabletopGame
    let renderer: GameRenderer
    let observer: GameObserver

    init() {
        let table = GameBoard()
        var setup = TableSetup(tabletop: table)

        // Add seats
        for i in 0..<4 {
            setup.add(seat: PlayerSeat(index: i))
        }

        // Add equipment
        setup.add(equipment: GameDie(id: .init(100)))
        for i in 0..<52 {
            setup.add(equipment: PlayingCard(id: .init(200 + i)))
        }

        // Add counters
        for i in 0..<4 {
            setup.add(counter: ScoreCounter(id: .init(i), value: 0))
        }

        // Register custom actions
        setup.register(action: CollectCoin.self)
        setup.register(action: FlipAllCards.self)

        // Create game
        tabletopGame = TabletopGame(tableSetup: setup)

        // Set up rendering
        renderer = GameRenderer()
        tabletopGame.addRenderDelegate(renderer)

        // Set up observation
        observer = GameObserver()
        observer.game = self
        tabletopGame.addObserver(observer)

        // Claim a seat
        tabletopGame.claimAnySeat()
    }
}
```

## Network and Multiplayer Coordination

Group Activities coordination is available through
`TabletopGame.coordinateWithSession(_:)`; Apple's group-gameplay sample uses
visionOS 26.0+ / Xcode 26.0+ APIs.

### Custom Network Coordinator

For non-GroupActivities multiplayer (e.g., local network), implement
`TabletopNetworkSessionCoordinator`:

```swift
class LocalNetworkCoordinator: TabletopNetworkSessionCoordinator {
    typealias Peer = NetworkPeer
    typealias NetworkSession = TabletopNetworkSession<LocalNetworkCoordinator>

    var networkSession: NetworkSession?

    func coordinateWithSession(_ session: NetworkSession) {
        self.networkSession = session
    }

    func sendMessage(_ data: Data,
                     to peers: Set<NetworkPeer>,
                     completion: (TabletopSendMessageResult) -> Void) {
        // Send via your transport layer
        completion(.success)
    }

    func sendMessageUnreliably(_ data: Data,
                                to peers: Set<NetworkPeer>,
                                completion: (TabletopSendMessageResult) -> Void) {
        // Send without delivery guarantee
        completion(.success)
    }

    func peerJoinedGame(_ peerID: NetworkPeer.ID) {
        networkSession?.addPeer(/* peer */)
    }

    func peerLeftGame(_ peerID: NetworkPeer.ID) {
        networkSession?.removePeer(/* peer */)
    }
}
```

### Arbiter Role

In multiplayer, one device acts as the arbiter (source of truth). The arbiter
validates actions and resolves conflicts.

```swift
// Become the arbiter
networkSession.becomeArbiter()

// Or follow another peer as arbiter
networkSession.followArbiter(hostPeer)
```

### Handling Network Lifecycle

```swift
// Start hosting
networkSession.start()

// Join an existing session
networkSession.join()

// Leave gracefully
networkSession.leave()

// Terminate the session (arbiter only)
networkSession.terminate()
```

## State Bookmarks and Undo

### Creating Bookmarks at Key Points

Save state at the start of each turn for undo support:

```swift
func startNewTurn(seatID: TableSeatIdentifier) {
    let bookmarkID = StateBookmarkIdentifier(turnNumber)
    game.addAction(.createBookmark(id: bookmarkID))
    game.addAction(.setTurn(matching: seatID))
}
```

### Restoring to a Bookmark

```swift
// Undo last turn
if let lastBookmark = game.bookmarks.last {
    game.jumpToBookmark(matching: lastBookmark)
}
```

### Observer Notification

```swift
func stateDidResetToBookmark(_ bookmarkID: StateBookmarkIdentifier) {
    // This callback is the completion/reconciliation point for the jump.
    game.withCurrentSnapshot { snapshot in
        refreshUI(from: snapshot)
        validateRestoredTurnInvariant(snapshot)
    }
}
```

Do not inspect the snapshot immediately after `jumpToBookmark` or blindly issue
another jump when local UI disagrees. Wait for this ordered callback, then
rebuild local UI from its snapshot. Keep confirm, rollback, and discard handling
in the main [Observer Patterns](#observer-patterns) implementation.

## Score Tracking

### Setting Up Counters per Player

```swift
// During setup: one counter per seat
for seatIndex in 0..<4 {
    setup.add(counter: ScoreCounter(id: .init(seatIndex), value: 0))
}
```

### Updating Scores

```swift
// Increment a player's score
game.withCurrentSnapshot { snapshot in
    let currentScore = snapshot.counter(matching: .init(seatIndex))?.value ?? 0
    game.addAction(.updateCounter(
        matching: .init(seatIndex),
        value: currentScore + points
    ))
}
```

### Reading Scores from Snapshot

```swift
game.withCurrentSnapshot { snapshot in
    for counter in snapshot.counters {
        print("Counter \(counter.id): \(counter.value)")
    }
}
```

## Debugging Techniques

### Debug Draw Options

```swift
// Draw all debug visuals
game.debugDraw(options: [.drawTable, .drawSeats, .drawEquipment])

// Draw only table boundaries
game.debugDraw(options: [.drawTable])

// Disable all debug visuals
game.debugDraw(options: [])
```

### Inspecting Snapshots

```swift
game.withCurrentSnapshot { snapshot in
    // List all equipment
    for id in snapshot.equipmentIDs() {
        let state = snapshot.state(matching: id)
        print("Equipment \(id.rawValue): \(String(describing: state))")
    }

    // List seat assignments
    for seat in snapshot.seats {
        print("Seat: \(seat)")
    }

    // Check whose turn it is
    print("Turn: \(snapshot.turn)")

    // List active cursors (interactions in progress)
    for cursor in snapshot.cursors {
        print("Cursor: player=\(cursor.playerID), "
              + "equipment=\(cursor.controlledEquipmentPose.id)")
    }
}
```

### Logging Observer Events

Wrap observer methods with logging during development:

```swift
func actionWasConfirmed(_ action: some TabletopAction,
                        oldSnapshot: TableSnapshot,
                        newSnapshot: TableSnapshot) {
    #if DEBUG
    print("[Observer] Confirmed: \(type(of: action)), "
          + "player=\(String(describing: action.playerID))")
    #endif
    // Normal handling...
}

func actionWasRolledBack(_ action: some TabletopAction,
                          snapshot: TableSnapshot) {
    #if DEBUG
    print("[Observer] Rolled back: \(type(of: action))")
    #endif
}
```
