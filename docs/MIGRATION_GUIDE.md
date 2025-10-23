# 📚 Documentation Migration Guide

> [!NOTE]
> **Documentation Reorganized!** We've restructured our documentation for better navigation and user experience.

This guide helps you find content in the new structure.

---

## 🗺️ Quick Navigation

**New to our docs?** Start at [Documentation Index](INDEX.md)

**Looking for something specific?** Use the mapping table below 👇

---

## 📋 Old → New Document Mapping

| Old Location | New Location | Notes |
|--------------|--------------|-------|
| `docs/QUICKSTART.md` | [`docs/GETTING_STARTED.md`](GETTING_STARTED.md) | Enhanced with more examples |
| `docs/CONFIGURATION_REFERENCE.md` | [`docs/USER_GUIDES/CONFIGURATION.md`](USER_GUIDES/CONFIGURATION.md) | Consolidated all config info |
| `docs/CLICKHOUSE_BACKEND_GUIDE.md` | [`docs/USER_GUIDES/BACKENDS.md`](USER_GUIDES/BACKENDS.md) | Includes OTLP comparison |
| `docs/PRIVACY_POLICY.md` | [`docs/USER_GUIDES/PRIVACY.md`](USER_GUIDES/PRIVACY.md) | Enhanced with flowcharts |
| `docs/TELEMETRY_DEVELOPMENT_GUIDE.md` | [`docs/DEVELOPER_GUIDES/ARCHITECTURE.md`](DEVELOPER_GUIDES/ARCHITECTURE.md) | Architecture deep dive |
| `docs/IMPLEMENTATION_GUIDE.md` | [`docs/DEVELOPER_GUIDES/IMPLEMENTATION.md`](DEVELOPER_GUIDES/IMPLEMENTATION.md) | More patterns added |
| `docs/INTEGRATION_TESTS.md` | [`docs/DEVELOPER_GUIDES/TESTING.md`](DEVELOPER_GUIDES/TESTING.md) | Consolidated all testing |
| `docs/INTEGRATION_TESTS_SUMMARY.md` | [`docs/DEVELOPER_GUIDES/TESTING.md`](DEVELOPER_GUIDES/TESTING.md) | Merged into TESTING.md |
| `docs/QUICK_REFERENCE.md` | [`docs/USER_GUIDES/QUICK_REFERENCE.md`](USER_GUIDES/QUICK_REFERENCE.md) | Moved to USER_GUIDES |
| `docs/CONVENTIONS.md` | [`docs/DEVELOPER_GUIDES/SDK_DIFFERENCES.md`](DEVELOPER_GUIDES/SDK_DIFFERENCES.md) | Enhanced comparison |
| N/A (New) | [`docs/REFERENCES/API_REFERENCE.md`](REFERENCES/API_REFERENCE.md) | Complete API docs |
| N/A (New) | [`docs/REFERENCES/ENVIRONMENT_VARIABLES.md`](REFERENCES/ENVIRONMENT_VARIABLES.md) | All env vars |
| N/A (New) | [`docs/REFERENCES/TROUBLESHOOTING.md`](REFERENCES/TROUBLESHOOTING.md) | Solutions guide |
| N/A (New) | [`docs/USER_GUIDES/SELF_HOSTING.md`](USER_GUIDES/SELF_HOSTING.md) | Infrastructure guide |
| N/A (New) | [`docs/DEVELOPER_GUIDES/CONTRIBUTING.md`](DEVELOPER_GUIDES/CONTRIBUTING.md) | Dev workflow |

---

## 🎯 Find by Topic

<details>
<summary><strong>Configuration & Setup</strong></summary>

- **General Configuration**: [USER_GUIDES/CONFIGURATION.md](USER_GUIDES/CONFIGURATION.md)
- **Environment Variables**: [REFERENCES/ENVIRONMENT_VARIABLES.md](REFERENCES/ENVIRONMENT_VARIABLES.md)
- **Backend Selection**: [USER_GUIDES/BACKENDS.md](USER_GUIDES/BACKENDS.md)
- **Self-Hosting**: [USER_GUIDES/SELF_HOSTING.md](USER_GUIDES/SELF_HOSTING.md)

</details>

<details>
<summary><strong>Privacy & Security</strong></summary>

- **Privacy Policy**: [USER_GUIDES/PRIVACY.md](USER_GUIDES/PRIVACY.md)
- **Security Best Practices**: [USER_GUIDES/SELF_HOSTING.md#security](USER_GUIDES/SELF_HOSTING.md#-security)
- **GDPR/CCPA Compliance**: [USER_GUIDES/PRIVACY.md#compliance](USER_GUIDES/PRIVACY.md#-compliance)

</details>

<details>
<summary><strong>Development & Testing</strong></summary>

- **Architecture**: [DEVELOPER_GUIDES/ARCHITECTURE.md](DEVELOPER_GUIDES/ARCHITECTURE.md)
- **Implementation Patterns**: [DEVELOPER_GUIDES/IMPLEMENTATION.md](DEVELOPER_GUIDES/IMPLEMENTATION.md)
- **Testing Guide**: [DEVELOPER_GUIDES/TESTING.md](DEVELOPER_GUIDES/TESTING.md)
- **Contributing**: [DEVELOPER_GUIDES/CONTRIBUTING.md](DEVELOPER_GUIDES/CONTRIBUTING.md)

</details>

<details>
<summary><strong>API & Reference</strong></summary>

- **API Documentation**: [REFERENCES/API_REFERENCE.md](REFERENCES/API_REFERENCE.md)
- **Quick Reference**: [USER_GUIDES/QUICK_REFERENCE.md](USER_GUIDES/QUICK_REFERENCE.md)
- **Python ↔ TypeScript Differences**: [DEVELOPER_GUIDES/SDK_DIFFERENCES.md](DEVELOPER_GUIDES/SDK_DIFFERENCES.md)
- **Troubleshooting**: [REFERENCES/TROUBLESHOOTING.md](REFERENCES/TROUBLESHOOTING.md)

</details>

---

## 🏗️ New Documentation Structure

```
docs/
├── INDEX.md                          # 📍 START HERE - Main navigation hub
├── GETTING_STARTED.md                # 🚀 5-minute quick start
├── USER_GUIDES/                      # 👨‍💻 Using the SDK
│   ├── CONFIGURATION.md
│   ├── BACKENDS.md
│   ├── PRIVACY.md
│   ├── SELF_HOSTING.md
│   └── QUICK_REFERENCE.md
├── DEVELOPER_GUIDES/                 # 🔧 Contributing & Development
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION.md
│   ├── TESTING.md
│   ├── SDK_DIFFERENCES.md
│   └── CONTRIBUTING.md
├── REFERENCES/                       # 📚 Quick Lookup
│   ├── API_REFERENCE.md
│   ├── ENVIRONMENT_VARIABLES.md
│   └── TROUBLESHOOTING.md
└── .archive/                         # 📦 Old docs (deprecated)
```

---

## ✨ What's New?

### 📍 Documentation Index
[**INDEX.md**](INDEX.md) is your new starting point:
- Quick navigation cards
- User journey flowcharts
- Documentation by audience
- Learning paths

### 🎨 Enhanced Content
All guides now feature:
- ✅ GitHub callouts (`> [!TIP]`, `> [!WARNING]`)
- 📊 Beautiful tables and comparisons
- 🎯 Mermaid diagrams (flowcharts, architecture)
- 🔄 Collapsible sections for better organization
- 💡 More code examples

### 🗂️ Better Organization
- **By Audience**: Getting Started → User Guides → Developer Guides
- **By Purpose**: Guides vs References
- **Cross-Referenced**: Easy navigation between related docs

---

## 🔗 Bookmarks to Update

If you have bookmarked any documentation, update to:

| Old Bookmark | New Bookmark |
|--------------|--------------|
| `docs/QUICKSTART.md` | [`docs/INDEX.md`](INDEX.md) or [`docs/GETTING_STARTED.md`](GETTING_STARTED.md) |
| Any old doc | [`docs/INDEX.md`](INDEX.md) ← Start here! |

---

## 📦 Archived Documents

Old documents are preserved in `docs/.archive/` with `.DEPRECATED` suffix for historical reference.

Each archived file includes a migration notice pointing to its replacement.

---

## ❓ Questions?

- **Can't find something?** Check [INDEX.md](INDEX.md) or [TROUBLESHOOTING.md](REFERENCES/TROUBLESHOOTING.md)
- **Found a broken link?** [Open an issue](https://github.com/namastexlabs/automagik-telemetry/issues)
- **Need help?** Join our [Discord](https://discord.gg/xcW8c7fF3R)

---

<p align="center">
  <strong>📚 Happy documenting!</strong><br>
  <em>Better docs = better developer experience</em>
</p>
