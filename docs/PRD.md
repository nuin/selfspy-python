# Product Requirements Document: Selfspy

**Document Version**: 1.0
**Last Updated**: 2025-10-22
**Status**: Implemented & Production-Ready
**Product Type**: Privacy-focused activity monitoring and analytics tool

---

## 1. Context & Why Now

- **Personal productivity analytics is a growing category** but most solutions require cloud services and sacrifice user privacy by sending sensitive activity data to external servers
- **Developer workflow optimization is critical** as knowledge workers spend significant time context-switching between applications, terminals, and projects without clear visibility into their patterns
- **Privacy regulations (GDPR, CCPA) make cloud-based tracking risky** for organizations and individuals who want to monitor activity without exposing sensitive data to third parties
- **Modern async Python patterns enable efficient local monitoring** with SQLAlchemy 2.0 and async/await making it feasible to build high-performance local-first applications
- **macOS provides robust accessibility APIs** that enable comprehensive activity tracking when users grant explicit permissions, creating an opportunity for native platform integration

---

## 2. Users & Jobs to Be Done (JTBD)

### Primary User Segments

**Individual Knowledge Workers**
- As a software developer, I need to understand where my time goes during coding sessions so that I can identify productivity patterns and reduce context-switching
- As a remote worker, I need to track my activity privately without employer surveillance so that I can self-optimize my workflow while maintaining autonomy
- As a productivity enthusiast, I need detailed analytics about my computer usage so that I can make data-driven decisions about tool usage and work habits

**Privacy-Conscious Professionals**
- As a security professional, I need activity monitoring that stores all data locally with encryption so that I can analyze work patterns without data exposure risk
- As a healthcare/legal professional, I need compliance-friendly monitoring so that I can track productivity while meeting HIPAA/attorney-client privilege requirements
- As an open-source contributor, I need transparent activity tracking so that I can verify what data is collected and how it's stored

**Technical Researchers & Analysts**
- As a UX researcher, I need granular application usage data so that I can study real-world interaction patterns for software design
- As a developer tools maker, I need terminal command analytics so that I can understand how developers actually use CLI tools in their workflow
- As a productivity researcher, I need long-term activity datasets so that I can identify seasonal patterns and behavioral trends

### Secondary User Segments

**Development Teams (Future)**
- As a team lead, I need aggregated anonymous activity patterns so that I can optimize team workflows without individual surveillance
- As a DevOps engineer, I need to understand terminal command patterns so that I can create better automation and improve developer experience

---

## 3. Business Goals & Success Metrics

### Business Goals

1. **Establish Selfspy as the privacy-first standard for personal activity monitoring** by providing comprehensive tracking without cloud dependencies or privacy compromises
2. **Enable deep productivity insights for technical users** through rich terminal analytics, development workflow tracking, and git integration
3. **Build a sustainable open-source project** with clear architecture, comprehensive documentation, and extensibility for community contributions
4. **Demonstrate technical excellence** through modern Python patterns (async/await, SQLAlchemy 2.0, Pydantic settings) that serve as reference implementation
5. **Support multiple platforms** with macOS as primary target and cross-platform fallback for broader adoption

### Leading Indicators (Early Signals)

- **Installation success rate**: Percentage of users who successfully complete setup with permissions granted
- **Daily active monitoring sessions**: Number of days per week users run the monitoring daemon
- **Terminal analytics adoption**: Percentage of users who enable and use terminal command tracking
- **Widget engagement**: Number of users who install and actively use desktop widgets
- **Configuration customization rate**: Percentage of users who modify default settings

### Lagging Indicators (Ultimate Success)

- **Monthly active users**: Target 1,000+ active installations within first year
- **Data retention**: Average user maintains monitoring for 90+ consecutive days
- **Community contributions**: 10+ external contributors submitting features or fixes
- **Documentation quality**: Support questions answered by existing docs (80%+ self-service rate)
- **Platform coverage**: Successful deployments on macOS (primary), Linux, Windows (fallback)

**Targets & Timeframes**

- **Q1**: Core monitoring stable with 100+ weekly active users
- **Q2**: Terminal analytics and widgets adopted by 50%+ of user base
- **Q3**: First community-contributed integrations or visualization tools
- **Q4**: Cross-platform support with Linux and Windows installations

---

## 4. Functional Requirements

### FR1: Core Activity Monitoring
**Requirement**: System shall continuously monitor keyboard, mouse, and window activity with configurable intervals

**Acceptance Criteria**:
- Monitor captures keystroke events with millisecond precision
- Mouse clicks (left, middle, right) and scroll events are tracked with coordinates
- Active window changes detected within 100ms of switch
- Process name, window title, and bundle ID captured for each window
- Monitoring runs continuously without user intervention after start
- Graceful shutdown on SIGTERM/SIGINT with data flush

### FR2: Encrypted Keystroke Storage
**Requirement**: All keystroke data shall be encrypted using AES-256 with user-provided password stored in system keychain

**Acceptance Criteria**:
- User prompted for password on first run
- Password stored securely in macOS Keychain (or platform equivalent)
- Keystroke text encrypted before database write using Fernet (PBKDF2 + AES-256)
- Password verification using magic string prevents incorrect password usage
- Encryption can be disabled via configuration for non-sensitive usage
- No plaintext keystroke data written to disk at any time

### FR3: Async Database Persistence
**Requirement**: Activity data shall be persisted to SQLite database using async SQLAlchemy 2.0 with proper buffering

**Acceptance Criteria**:
- Database operations are non-blocking using aiosqlite
- Keystroke buffer flushes after 1 second of inactivity or 50 keystrokes
- Click and scroll events stored with button type and coordinates
- Window changes persisted with geometry, screen info, and timestamps
- Database schema includes proper indexes for query performance
- Foreign key relationships maintained for data integrity
- Database size managed with configurable cleanup thresholds

### FR4: Platform-Specific Integration
**Requirement**: System shall use native macOS APIs for optimal tracking with cross-platform fallback

**Acceptance Criteria**:
- macOS: Uses PyObjC with Quartz and ApplicationServices frameworks
- macOS: Checks for Accessibility permissions and prompts if missing
- macOS: Opens System Settings directly to permission page
- Fallback: Uses pynput for keyboard/mouse on Linux/Windows
- Platform detection automatic based on `platform.system()`
- Bundle ID capture on macOS for application identification
- Cross-platform operation without macOS-specific features

### FR5: Rich CLI Visualizations
**Requirement**: System shall provide multiple CLI commands for viewing statistics with rich terminal output

**Acceptance Criteria**:
- `selfspy viz enhanced`: Shows productivity dashboard with charts and heatmaps
- `selfspy viz timeline`: Displays chronological activity timeline
- `selfspy viz live`: Real-time updating dashboard (5-second refresh)
- Bar charts rendered using Rich library with colored blocks
- Time-based heatmap shows activity by 6-hour blocks (Night/Morning/Day/Evening)
- Productivity score calculated from keystrokes, windows, process count
- Top applications ranked by keystroke count and click count
- All visualizations support date range filtering (--days parameter)

### FR6: Terminal Command Tracking
**Requirement**: System shall track terminal commands from shell history with project context

**Acceptance Criteria**:
- Monitors bash, zsh, and fish history files
- Commands parsed from different shell history formats
- Working directory and git branch captured for each command
- Project type detected (Python, Node, Rust, Go, Java, C/C++)
- Commands categorized (git, npm, python, build, editor, file, system, network)
- Dangerous commands flagged (rm, sudo, chmod, etc.)
- Common commands filtered (ls, cd, pwd, clear)
- Duplicate commands within same session deduplicated by hash
- Background polling every 2 seconds for new commands

### FR7: Desktop Widgets
**Requirement**: System shall provide native macOS desktop widgets for always-visible activity display

**Acceptance Criteria**:
- Python/PyObjC implementation for rapid development
- Always-on-top windows that don't interfere with workflow
- Drag-and-drop repositioning anywhere on screen
- Auto-refresh data every 5-10 seconds
- Display real-time keystroke, click, and application statistics
- Terminal activity integration showing recent commands
- Productivity metrics calculated and displayed
- Multiple widget types (simple, advanced, terminal-focused)
- Configuration management for widget preferences

### FR8: Privacy Controls
**Requirement**: System shall provide comprehensive privacy controls via configuration

**Acceptance Criteria**:
- Configurable excluded applications (default: 1Password, Keychain Access, System Settings)
- Process bundle exclusion list for macOS
- Privacy mode enables stricter filtering
- Optional screenshot capture (disabled by default)
- Screenshot exclusion list separate from activity tracking
- Database size limits with auto-cleanup
- Backup management with rotation
- No data transmission outside local machine
- All settings via Pydantic Settings with environment variables

### FR9: Configuration Management
**Requirement**: System shall support flexible configuration via environment variables, .env files, and code defaults

**Acceptance Criteria**:
- Settings class using Pydantic Settings with validation
- Environment variables prefixed with `SELFSPY_`
- .env file support in data directory or project root
- Database path, encryption, intervals, exclusions all configurable
- Field validators prevent invalid configurations
- Type-safe settings with Python type hints
- Computed properties for derived values (database_path)
- Settings documentation in code and external docs

### FR10: Statistics and Analytics
**Requirement**: System shall provide comprehensive analytics across time periods with multiple output formats

**Acceptance Criteria**:
- Daily, weekly, monthly aggregations
- Per-application keystroke and click counts
- Window visit frequency and duration
- Hourly activity heatmaps for pattern detection
- Productivity scoring algorithm with level classification
- Daily averages calculated across time period
- Timeline view showing chronological activity
- Support for text, JSON, CSV output formats
- Date range filtering with ISO 8601 date format

---

## 5. Non-Functional Requirements

### Performance
- **Response Time**: Window change detection within 100ms of actual switch
- **Throughput**: Support 1000+ keystrokes per minute without data loss
- **CPU Usage**: Less than 2% CPU usage during normal monitoring on modern hardware
- **Memory**: Under 100MB RAM footprint for monitoring daemon
- **Database Write Latency**: Async writes complete within 50ms

### Scale
- **Data Volume**: Support years of continuous monitoring (100GB+ database)
- **Concurrent Sessions**: Handle multiple terminal sessions simultaneously
- **Window Tracking**: Track 100+ application switches per hour
- **History Processing**: Parse shell history files with 10,000+ commands
- **Widget Updates**: Refresh widgets without UI lag or database lock contention

### SLOs/SLAs
- **Uptime**: Monitoring daemon runs 99.5% of time without crashes
- **Data Integrity**: Zero data loss during graceful shutdown
- **Query Performance**: Statistics generation completes in under 3 seconds
- **Startup Time**: Monitoring starts within 2 seconds of command
- **Permission Check**: Accessibility permission verification in under 1 second

### Privacy
- **Data Locality**: All data stored locally in `~/.selfspy/` by default
- **Encryption At Rest**: AES-256 encryption for all keystroke text
- **Password Security**: Passwords stored in system keychain, never in plaintext
- **No Telemetry**: Zero data transmission to external servers
- **Audit Trail**: All database operations logged in structured logs
- **Compliance Ready**: Architecture supports GDPR, HIPAA, SOC2 data requirements

### Security
- **Authentication**: Password required for encrypted keystroke access
- **Authorization**: Only process owner can access database files (filesystem permissions)
- **Encryption**: PBKDF2 key derivation with 100,000 iterations
- **Key Management**: Fernet symmetric encryption with URL-safe base64
- **Dangerous Command Detection**: Flags commands like `rm -rf`, `sudo`, `chmod`
- **Code Security**: No eval, no arbitrary code execution, no network sockets

### Observability
- **Structured Logging**: All logs use structlog with context
- **Debug Mode**: Configurable debug logging for troubleshooting
- **Error Handling**: All exceptions caught and logged with context
- **Live Monitoring**: Real-time display shows current monitoring state
- **Database Inspection**: Direct SQLite access for advanced users
- **Metrics**: Built-in productivity scoring and activity metrics

---

## 6. Scope Definition

### In Scope

- **Activity Monitoring**: Keystrokes, mouse clicks, scrolls, window changes
- **Encryption**: AES-256 for keystroke data with password protection
- **Platform Support**: macOS (full), Linux/Windows (fallback)
- **Terminal Analytics**: Command tracking for bash/zsh/fish
- **Visualizations**: Rich CLI dashboards, charts, timelines, heatmaps
- **Desktop Widgets**: Python/PyObjC implementation for macOS
- **Configuration**: Environment variables, .env files, Pydantic settings
- **Privacy Controls**: Application exclusions, privacy mode, optional features
- **Documentation**: Installation, usage, configuration, architecture, troubleshooting
- **Database**: SQLite with async SQLAlchemy 2.0, proper indexes
- **CLI Commands**: single `selfspy` entrypoint with subcommands `daemon`, `tui`, `stats`, `viz`, `terminal`, `migrate`, `check-permissions`

### Out of Scope

- **Cloud Sync**: No cloud storage or backup features
- **Multi-User**: Single-user per installation only
- **Web Interface**: No web-based dashboard (CLI and widgets only)
- **Mobile Apps**: No iOS/Android clients
- **Team Features**: No multi-user analytics or team dashboards
- **Real-time Collaboration**: No shared monitoring or data sync
- **Screenshot OCR**: No text extraction from screenshots
- **Video Recording**: No screen recording capabilities
- **Network Activity**: No network traffic monitoring
- **File System Monitoring**: No file change tracking
- **API Endpoints**: No REST API or webhook integrations (FastAPI imported but not exposed)

### Future Considerations

- **Web Dashboard**: Browser-based visualization for richer charts (Plotly already imported)
- **Plugin System**: Extension points for custom trackers or visualizations
- **Export Formats**: Additional export options (Excel, PDF reports)
- **AI Insights**: Machine learning for pattern detection and recommendations
- **Team Analytics**: Anonymous aggregation for team productivity insights
- **Cross-Device**: Sync activity across multiple machines (privacy-preserving)
- **Integration APIs**: Hooks for calendar, task managers, time tracking tools
- **Mobile Companion**: View stats on phone without full tracking
- **Voice Commands**: Optional voice activity tracking
- **Advanced Filtering**: SQL-like queries or GUI filter builder

---

## 7. Rollout Plan

### Phase 1: Core Monitoring (Implemented)
**Status**: Complete and stable

**Milestones**:
- ActivityMonitor orchestration with async/await patterns
- Platform-specific trackers (macOS with PyObjC, cross-platform fallback)
- SQLite database with SQLAlchemy 2.0 async
- Encryption with Fernet and keychain integration
- Basic CLI commands (`selfspy daemon`)

**Success Gates**:
- Monitoring runs continuously without crashes for 24+ hours
- Database grows predictably with activity
- CPU/memory usage within acceptable thresholds
- Permissions check works on fresh macOS install

### Phase 2: Analytics & Visualization (Implemented)
**Status**: Complete and stable

**Milestones**:
- Rich CLI visualizations (`selfspy viz enhanced`, timeline, live)
- Statistical aggregations with proper SQL queries
- Productivity scoring algorithm
- Time-based heatmaps and bar charts
- Terminal command tracking integration

**Success Gates**:
- Stats generation completes in under 3 seconds for 7-day periods
- Visualizations render correctly in various terminal emulators
- No cartesian product issues in SQL queries
- Terminal tracking captures 95%+ of executed commands

### Phase 3: Desktop Widgets (Implemented)
**Status**: Complete with Python/PyObjC implementation

**Milestones**:
- Simple widget for development and testing
- Advanced widget system with multiple types
- Widget configuration management
- Data integration with real-time updates
- Drag-and-drop positioning

**Success Gates**:
- Widgets update without blocking main monitoring
- No database lock contention between widgets and daemon
- Widgets maintain position across restarts
- Memory usage acceptable with multiple widgets

### Phase 4: Documentation & Polish (Implemented)
**Status**: Comprehensive documentation in place

**Milestones**:
- Installation guide with dependency management (uv)
- Usage guide with command examples
- Configuration reference with all settings
- Architecture documentation with design decisions
- Troubleshooting guide for common issues

**Success Gates**:
- New users can install without asking questions (80%+ success)
- All configuration options documented with examples
- Common errors have documented solutions
- Architecture doc enables contributor onboarding

### Guardrails

- **Data Loss Prevention**: Before any schema changes, verify backup and restore procedures
- **Performance Regression**: Automated performance tests prevent CPU/memory increases
- **Privacy Validation**: Manual review of all data collection code for privacy compliance
- **Backward Compatibility**: Database migrations must preserve existing data
- **Permission Handling**: Never proceed with monitoring without explicit user permission grant

### Kill-Switch Criteria

- **Data Corruption**: More than 1% of database writes fail integrity checks
- **Privacy Breach**: Any evidence of data transmission outside local machine
- **Performance Collapse**: CPU usage exceeds 10% or memory exceeds 500MB
- **Permission Violations**: Attempt to bypass permission checks or accessibility requirements
- **Security Vulnerability**: Discovery of unencrypted keystroke storage or password exposure

---

## 8. Risks & Open Questions

### Technical Risks

**Risk**: macOS permission model changes break tracking in future OS versions
**Mitigation**: Modular platform abstraction allows quick updates; fallback tracker as safety net

**Risk**: SQLite database lock contention with multiple readers (widgets + CLI)
**Mitigation**: Async database access with connection pooling; widget queries use read-only connections

**Risk**: Shell history parsing breaks with custom shell configurations
**Mitigation**: Regex patterns handle multiple formats; graceful degradation for unparseable lines

**Risk**: Encryption key loss results in unrecoverable keystroke data
**Mitigation**: Document backup procedures; consider optional key recovery mechanism in future

**Risk**: Large database files (100GB+) cause performance degradation
**Mitigation**: Configurable auto-cleanup thresholds; database size monitoring; future archival feature

### Business/Market Risks

**Risk**: Privacy concerns prevent adoption despite local-first architecture
**Mitigation**: Transparent open-source code; comprehensive privacy documentation; optional features

**Risk**: Similar tools with better UX or features fragment user base
**Mitigation**: Focus on technical excellence and privacy; build community around extensibility

**Risk**: Lack of cross-platform support limits adoption to macOS users only
**Mitigation**: Fallback tracker provides basic functionality; Linux as next platform priority

**Risk**: Open-source sustainability challenges without funding model
**Mitigation**: Keep core simple and maintainable; accept community contributions; explore sponsorship

### Open Questions

**Q1**: Should we expose FastAPI endpoints for remote widget access?
**Context**: FastAPI/Uvicorn dependencies already included but not used
**Decision Needed**: Evaluate privacy implications vs. convenience for remote dashboards

**Q2**: What is the optimal database cleanup strategy for long-term users?
**Context**: Current auto-cleanup based on size threshold, but no time-based archival
**Decision Needed**: Define retention policies and archival format for historical data

**Q3**: Should terminal tracking support custom shell configurations?
**Context**: Currently handles standard bash/zsh/fish, but many users customize heavily
**Decision Needed**: Define plugin system or configuration for custom parsing

**Q4**: How should we handle screenshot features given privacy concerns?
**Context**: Infrastructure exists but disabled by default; unclear if valuable enough
**Decision Needed**: Either enhance with OCR/analysis or remove to reduce attack surface

**Q5**: What is the community contribution model for new trackers or widgets?
**Context**: No formal plugin system or contribution guidelines beyond standard OSS
**Decision Needed**: Define extension points, API stability guarantees, and review process

### Dependencies

**Internal Dependencies**:
- Pydantic Settings for configuration management
- SQLAlchemy async session management
- Rich library for terminal visualizations
- Structlog for logging infrastructure

**External Dependencies**:
- macOS Accessibility permissions (user-granted)
- System keychain for password storage
- Shell history file access (bash/zsh/fish)
- PyObjC frameworks for native macOS features

**Platform Dependencies**:
- Python 3.10+ runtime
- SQLite 3.8+ (included with Python)
- macOS 10.12+ for full features
- Terminal emulator with color support for visualizations

---

## Technical Architecture Overview

### System Components

```
ActivityMonitor (Orchestrator)
├── Platform Trackers
│   ├── MacOSInputTracker (PyObjC-based)
│   ├── MacOSWindowTracker (Quartz API)
│   └── FallbackTracker (pynput-based)
├── TerminalTracker (Shell history monitoring)
└── ActivityStore (Async SQLAlchemy)
    └── SQLite Database (encrypted keystrokes)

CLI Layer (single `selfspy` entrypoint)
├── selfspy daemon         (headless monitoring)
├── selfspy tui            (interactive TUI)
├── selfspy stats          (basic statistics)
├── selfspy viz            (rich visualizations)
├── selfspy terminal       (terminal analytics)
├── selfspy migrate        (alembic migrations)
└── selfspy check-permissions

Desktop Widgets (macOS)
├── PyObjC Implementation
├── Data Integration Layer
└── Widget Configuration
```

### Data Flow

1. **Input Events**: Platform tracker captures keyboard/mouse/window events
2. **Buffering**: Events buffered in memory until flush threshold
3. **Encryption**: Keystroke text encrypted with Fernet before storage
4. **Async Write**: ActivityStore persists to SQLite asynchronously
5. **Querying**: CLI tools and widgets query database for statistics
6. **Visualization**: Rich library renders charts and dashboards

### Technology Stack

- **Language**: Python 3.10+ (async/await, type hints)
- **Database**: SQLite with aiosqlite and SQLAlchemy 2.0
- **Encryption**: cryptography library (Fernet with PBKDF2)
- **Configuration**: Pydantic Settings with environment variables
- **CLI**: Typer with Rich for terminal UI
- **Platform**: PyObjC for macOS, pynput for cross-platform
- **Logging**: structlog with structured logging
- **Dependency Management**: uv for fast, reliable installs

---

## Appendix: Key Design Decisions

### Why SQLite?
- Embedded database requires no server setup
- Excellent performance for local analytics workloads
- Battle-tested with billions of deployments
- Built-in Python support via aiosqlite
- File-based storage aligns with privacy goals

### Why Async SQLAlchemy?
- Non-blocking database operations prevent UI lag
- Future-proof for web dashboard or API endpoints
- Modern Python best practices (async/await)
- Better concurrency model for background tracking
- Enables efficient buffering and batching

### Why Pydantic Settings?
- Type-safe configuration with validation
- Environment variable support for deployment
- .env file integration for development
- Auto-generated documentation from types
- Computed properties for derived settings

### Why Rich Library?
- Beautiful terminal output without custom rendering
- Cross-platform terminal compatibility
- Built-in support for tables, charts, panels
- Live updating displays for real-time monitoring
- Extensive documentation and examples

### Why Local-First Architecture?
- Privacy by design (no data leaves machine)
- No cloud costs or server maintenance
- Works offline without limitations
- User owns all data in accessible format
- Compliance-friendly for regulated industries

---

## Success Criteria Summary

Selfspy is successful when:

1. **Users trust it**: Privacy-conscious users recommend it to peers based on transparent architecture
2. **It provides value**: Users gain actionable insights into productivity patterns within first week
3. **It's maintainable**: New contributors can understand codebase and add features successfully
4. **It's reliable**: Users run monitoring continuously without concerns about crashes or data loss
5. **It's private**: No privacy incidents, no data leaks, no surveillance concerns

---

**Document Prepared By**: Product analysis from implemented codebase
**Implementation Status**: Production-ready, actively maintained
**Next Review**: Quarterly or upon significant feature additions
