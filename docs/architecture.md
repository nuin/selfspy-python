# Architecture Documentation

## Overview

Selfspy is built with modern Python practices using async/await, SQLAlchemy 2.0, and platform-specific integrations. The architecture follows a layered approach with clear separation of concerns.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                            │
│                  (Typer, Rich, Structlog)                    │
├─────────────────────────────────────────────────────────────┤
│                    Activity Monitor                          │
│              (Event Loop Orchestration)                      │
├──────────────────────┬──────────────────────────────────────┤
│  Platform Trackers   │       Activity Store                 │
│  - MacOS (PyObjC)    │  (Async SQLAlchemy)                 │
│  - Linux (pynput)    │                                      │
│  - Windows (pynput)  │                                      │
├──────────────────────┴──────────────────────────────────────┤
│                    Data Models (SQLAlchemy)                  │
│         Process → Window → Keys/Clicks                       │
├─────────────────────────────────────────────────────────────┤
│                    SQLite Database                           │
│              (Encrypted keystroke data)                      │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. CLI Layer (`src/cli.py`)

**Responsibility:** User interface and command orchestration

**Key Features:**
- Typer for command structure
- Rich for formatted output
- Structlog for structured logging
- Signal handling for graceful shutdown

**Main Commands:**
- `selfspy daemon`: Begin monitoring
- `selfspy check-permissions`: Verify macOS permissions
- `selfspy stats`: View statistics
- `selfspy viz`: Enhanced visualizations
- `selfspy terminal`: Terminal analytics

**Entry Point:**
```python
app = typer.Typer()

@app.command()
def start(...):
    # Initialize components
    # Start async event loop
    # Handle signals
```

### 2. Activity Monitor (`src/activity_monitor.py`)

**Responsibility:** Orchestrate tracking and coordinate components

**Architecture:**
```python
class ActivityMonitor:
    def __init__(self, settings, store, debug):
        # Platform-specific trackers
        self.window_tracker = MacOSWindowTracker()
        self.input_tracker = MacOSInputTracker(callbacks)
        self.terminal_tracker = TerminalTracker()

    async def start(self):
        # Start event loop
        # Monitor active window
        # Flush buffers periodically
```

**Key Responsibilities:**
1. Platform detection and tracker initialization
2. Event loop management
3. Callback coordination
4. Live statistics display
5. Graceful shutdown

**Event Flow:**
```
User Input → Platform Tracker → ActivityMonitor Callback
→ Buffer → Periodic Flush → ActivityStore → Database
```

### 3. Activity Store (`src/activity_store.py`)

**Responsibility:** Async data persistence layer

**Key Features:**
- Async SQLAlchemy with aiosqlite
- Non-blocking database operations
- Session management
- Encryption integration

**Core Methods:**
```python
class ActivityStore:
    async def update_window_info(process, window, bundle, geometry)
    async def store_keys(text)
    async def store_click(button, x, y, distance)
    async def store_terminal_command(command, cwd, exit_code)
```

**Database Session Pattern:**
```python
async with self.async_session() as session:
    async with session.begin():
        # Operations automatically committed
        process = await session.scalar(select(Process)...)
        session.add(window)
        await session.flush()
```

### 4. Platform Abstraction (`src/platform/`)

**Responsibility:** Cross-platform input/window tracking

**Structure:**
```
platform/
├── base.py              # Abstract base classes
├── darwin.py            # macOS window and input tracking
├── fallback.py          # Cross-platform fallback
├── input_tracker.py     # Generic input tracker
└── screen_capture.py    # Screenshot functionality
```

**Base Classes:**
```python
class WindowTracker(ABC):
    @abstractmethod
    def get_active_window(self) -> WindowInfo:
        pass

class InputTracker(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass
```

**macOS Implementation:**
```python
class MacOSWindowTracker(WindowTracker):
    def get_active_window(self):
        # Use PyObjC to access macOS APIs
        # Quartz.CGWindowListCopyWindowInfo
        # Extract bundle ID, title, geometry
```

**Runtime Selection:**
```python
if platform.system() == "Darwin":
    tracker = MacOSWindowTracker()
else:
    tracker = FallbackWindowTracker()
```

### 5. Data Models (`src/models.py`)

**Responsibility:** Database schema and ORM

**Schema Design:**
```python
Process (1) ──< (N) Window (1) ──< (N) Keys
                         │
                         └──< (N) Click

# One process has many windows
# Each window has many keystroke/click records
```

**Models:**

```python
class Process(Base):
    id: int
    name: str
    bundle_id: str  # macOS bundle identifier
    windows: list[Window]
    keys: list[Keys]
    clicks: list[Click]

class Window(Base):
    id: int
    title: str
    process_id: int
    bundle_id: str
    is_minimized: bool
    is_fullscreen: bool
    geometry_x, geometry_y, geometry_width, geometry_height
    screen_width, screen_height, display_index

class Keys(Base):
    id: int
    text: bytes  # Encrypted
    count: int
    process_id: int
    window_id: int

class Click(Base):
    id: int
    button: int  # 1=left, 2=middle, 3=right, 4/5=scroll
    x, y: int
    move_distance: int
    move_points: str  # JSON
    process_id: int
    window_id: int
```

**Indexes for Performance:**
```python
Index("ix_process_name_created", Process.name, Process.created_at)
Index("ix_window_title_created", Window.title, Window.created_at)
Index("ix_click_coords", Click.x, Click.y)
Index("ix_click_timestamp", Click.created_at)
```

### 6. Encryption (`src/encryption.py`)

**Responsibility:** Keystroke data encryption

**Implementation:**
- AES-256 encryption via `cryptography` library
- Password stored in system keychain via `keyring`
- Password verification file for database access

**Key Functions:**
```python
def create_cipher(password: str) -> Cipher:
    # Derive key from password
    # Create AES cipher

def check_password(data_dir: Path, cipher: Cipher):
    # Verify password against stored digest

# Usage in Keys model
def decrypt_text(self, cipher) -> str:
    return cipher.decrypt(self.text).decode('utf-8')
```

### 7. Configuration (`src/config.py`)

**Responsibility:** Settings management

**Implementation:**
- Pydantic Settings for validation
- Environment variable support (`SELFSPY_*`)
- `.env` file loading
- Field validation

**Example:**
```python
class Settings(BaseSettings):
    data_dir: Path = Path.home() / ".selfspy"
    encryption_enabled: bool = True
    privacy_mode: bool = False

    @field_validator("data_dir")
    def validate_data_dir(cls, v):
        v.mkdir(parents=True, exist_ok=True)
        return v

    model_config = ConfigDict(
        env_prefix="SELFSPY_",
        env_file=".env"
    )
```

## Data Flow

### Input Event Flow

```
1. User types/clicks
2. OS generates event
3. Platform tracker captures event
   ├─ macOS: Quartz event tap
   └─ Other: pynput listener
4. Tracker invokes callback
5. ActivityMonitor buffers event
6. Periodic flush (1 second)
7. ActivityStore encrypts & stores
8. SQLite persists to disk
```

### Window Change Flow

```
1. User switches window/app
2. Window tracker polls (0.1s interval)
3. Detects change
4. ActivityMonitor._check_active_window()
5. Creates new Window record
6. Updates current_window_id
7. Future keys/clicks associate with new window
```

### Query Flow (Statistics)

```
1. User runs: selfspy stats / selfspy viz
2. Create read-only ActivityStore
3. Query SQLAlchemy models
4. Decrypt keystroke data (if needed)
5. Aggregate statistics
6. Format output (Rich/Plotly)
7. Display to user
```

## Async Architecture

### Event Loop Management

```python
# In cli.py start command
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Signal handlers
def signal_handler(signum, frame):
    loop.create_task(monitor.stop())
    loop.stop()

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Run monitor
loop.run_until_complete(monitor.start())
```

### Async Store Operations

All database operations are async to prevent blocking:

```python
# Non-blocking writes
await store.update_window_info(...)
await store.store_keys(...)
await store.store_click(...)

# Session management
async with self.async_session() as session:
    async with session.begin():
        # Transactions auto-commit
        pass
```

## Desktop Widgets Architecture

### Python/PyObjC Implementation

```
Widget Application (PyObjC NSApplication)
├── Multiple NSWindow instances
│   ├── Custom drawing (drawRect)
│   ├── Event handling (mouse events)
│   └── Data integration (async queries)
├── Timer-based refresh
└── Drag & drop positioning
```

**Key Components:**
```python
class ActivityWidget(NSWindow):
    def drawRect_(self, rect):
        # Custom drawing with Cocoa APIs

    def mouseDragged_(self, event):
        # Handle repositioning

    def updateData(self):
        # Query ActivityStore
        # Refresh display
```

## Performance Considerations

### Database Performance

1. **Indexed Queries**: All common queries use indexes
2. **Batch Writes**: Buffer events before writing
3. **Async I/O**: Non-blocking database operations
4. **Connection Pooling**: SQLAlchemy session management

### Memory Management

1. **Event Buffering**: Limited buffer size (1 second timeout)
2. **Session Cleanup**: Expire on commit prevents memory leaks
3. **Periodic Flushing**: Prevents buffer growth

### Platform Optimization

1. **Native APIs**: PyObjC for macOS (faster than pynput)
2. **Event Taps**: Low-level monitoring vs polling
3. **Selective Tracking**: Exclude system apps to reduce noise

## Security Architecture

### Threat Model

**Protected Against:**
- Unauthorized access to keystroke data
- Accidental exposure of sensitive text
- Database file theft (encrypted data)

**Not Protected Against:**
- Memory inspection while running
- Physical access to unlocked machine
- Keylogger with password capture

### Security Measures

1. **Encryption**: AES-256 for keystroke data
2. **Keychain Storage**: OS-level password security
3. **Application Exclusions**: Skip password managers
4. **Privacy Mode**: Enhanced restrictions
5. **File Permissions**: Restrictive database permissions

## Extension Points

### Adding New Platform Support

1. Implement `WindowTracker` base class
2. Implement `InputTracker` base class
3. Add platform detection in `activity_monitor.py`
4. Test with fallback mode

### Adding New Visualizations

1. Create new command in `enhanced_stats.py`
2. Query ActivityStore for data
3. Format with Plotly/Rich
4. Add to CLI

### Adding New Tracking

1. Add model to `models.py`
2. Add store method to `activity_store.py`
3. Add tracker callback to `activity_monitor.py`
4. Update platform trackers

## Testing Strategy

### Unit Tests
- Model relationships (`tests/test_models.py`)
- Configuration validation
- Encryption/decryption

### Integration Tests
- Database operations
- Platform tracker integration
- Async store operations

### Platform Tests
- macOS permission checking
- PyObjC framework availability
- Fallback behavior

## Deployment Architecture

### As User Service

```
User Login
└── LaunchAgent/systemd service
    └── selfspy daemon
        ├── Check permissions
        ├── Load configuration
        ├── Initialize database
        └── Begin monitoring
```

### With Desktop Widgets

```
User Session
├── selfspy daemon (background)
└── selfspy_desktop_advanced.py (foreground)
    └── Queries same database
```

## Next Steps

- [Installation Guide](installation.md) - Setup instructions
- [Usage Guide](usage.md) - How to use Selfspy
- [Configuration](configuration.md) - Customize settings
- [Troubleshooting](troubleshooting.md) - Common issues
