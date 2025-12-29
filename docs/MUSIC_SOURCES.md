# Best Royalty-Free Music Sources for Work-Focused Videos

This guide covers the best sources for royalty-free, YouTube-monetization-safe music for lofi/ambient/focus video production.

## Quick Recommendations

| Source | Cost | License | Best For | Bulk Download |
|--------|------|---------|----------|---------------|
| **Pixabay Music** | Free | CC0-like | Quick start | Manual |
| **Free Music Archive** | Free | CC licenses | Large variety | Manual |
| **Mixkit** | Free | Royalty-free | Lofi/ambient | Manual |
| **YouTube Audio Library** | Free | YouTube only | YouTube-safe | Manual |
| **Epidemic Sound** | $15/mo | Full license | Professional | API available |
| **Artlist** | $200/yr | Lifetime use | Premium quality | Bulk download |

---

## Free Sources (Best for Starting Out)

### 1. Pixabay Music
**URL**: https://pixabay.com/music/

- **License**: Pixabay License (similar to CC0, no attribution required)
- **Genres**: Lofi, ambient, chill, corporate, cinematic
- **Quality**: High-quality, curated tracks
- **Monetization**: Safe for YouTube monetization
- **Download**: Manual (no bulk download API)

**Best search terms for focus music**:
- "lofi hip hop"
- "ambient study"
- "chill beats"
- "focus music"
- "concentration"

### 2. Free Music Archive (FMA)
**URL**: https://freemusicarchive.org/

- **License**: Various Creative Commons (check each track)
- **Genres**: Every genre imaginable
- **Quality**: Variable (community uploads)
- **Monetization**: Depends on license (CC0 and CC-BY are safe)
- **Download**: Manual, some bulk tools exist

**Recommended categories**:
- Electronic > Ambient
- Instrumental > Lo-Fi
- Experimental > Drone

**Important**: Always check the specific license. Look for:
- CC0 (Public Domain) - Best, no restrictions
- CC-BY (Attribution) - Must credit in description
- Avoid CC-NC (Non-Commercial) for monetized videos

### 3. Mixkit
**URL**: https://mixkit.co/free-stock-music/

- **License**: Mixkit License (free for commercial use)
- **Genres**: Lofi, ambient, cinematic, corporate
- **Quality**: Professional quality
- **Monetization**: Safe for YouTube
- **Download**: Manual

**Best categories**:
- Lo-Fi
- Ambient
- Chill
- Soft

### 4. YouTube Audio Library
**URL**: https://studio.youtube.com/channel/UC/music (from Creator Studio)

- **License**: YouTube-specific (safe for YouTube only)
- **Genres**: All genres
- **Quality**: Professional
- **Monetization**: Guaranteed safe for YouTube
- **Download**: Manual from Creator Studio

**Access**: YouTube Studio > Audio Library

---

## Paid Sources (Best for Scale)

### 5. Epidemic Sound
**URL**: https://www.epidemicsound.com/

- **Cost**: $15/month (Personal) or $49/month (Commercial)
- **Tracks**: 50,000+ tracks, 90,000+ sound effects
- **License**: Full coverage while subscribed
- **API**: Yes - can integrate for bulk download
- **Best for**: High-volume production

**Pros**:
- Huge library of curated content
- No copyright claims while subscribed
- Great search/filtering
- API for automation

**Cons**:
- Must maintain subscription for continued use
- Claims may appear if subscription lapses

### 6. Artlist
**URL**: https://artlist.io/

- **Cost**: $199/year (Music) or $299/year (Music + SFX)
- **Tracks**: 30,000+ tracks
- **License**: Lifetime license for downloaded tracks
- **Best for**: Premium quality, long-term use

**Pros**:
- Keep tracks forever after download
- High production quality
- No claims ever on downloaded tracks
- Good mobile app for browsing

**Cons**:
- Higher upfront cost
- Smaller library than Epidemic Sound

### 7. Soundful (AI-Generated)
**URL**: https://soundful.com/

- **Cost**: Free tier + paid plans
- **Tracks**: AI-generated unique tracks
- **License**: Royalty-free
- **Best for**: Unique, never-before-heard music

**Pros**:
- Infinite unique tracks
- No copyright issues possible
- Customize tempo, mood, length

**Cons**:
- AI music quality varies
- May sound "generic"

---

## Workflow for Mass Production

### Strategy 1: Curated Local Library (Recommended)
1. Download 100-200 tracks from free sources
2. Organize by mood/tempo in folders
3. Use `audio.source: "local"` in config
4. Set `audio.recursive: true` to scan subfolders

**Folder structure**:
```
music/
├── lofi/
│   ├── chill/
│   └── upbeat/
├── ambient/
│   ├── nature/
│   └── electronic/
└── focus/
    ├── piano/
    └── minimal/
```

### Strategy 2: Google Drive Sync
1. Download tracks to Google Drive folder
2. Share folder with service account
3. Use `audio.source: "drive"` in config
4. Add new tracks anytime - they auto-sync

### Strategy 3: Rotating Playlists
Create multiple configs for variety:
```yaml
# config_lofi.yaml
audio:
  local_folder: "music/lofi"

# config_ambient.yaml
audio:
  local_folder: "music/ambient"

# config_focus.yaml
audio:
  local_folder: "music/focus"
```

Run different configs on different days.

---

## Avoiding Copyright Claims

### Always Safe
- CC0 (Public Domain)
- Tracks from paid services while subscribed
- YouTube Audio Library (for YouTube only)
- Your own original music

### Usually Safe (Verify First)
- CC-BY (Attribution required)
- Pixabay License
- Mixkit License

### Risky (Avoid)
- CC-NC (Non-Commercial) - Can't monetize
- CC-ND (No Derivatives) - Can't use as background
- "Free for personal use" - Usually means no commercial
- SoundCloud uploads without clear license

### What to Include in Video Description

For CC-BY tracks:
```
Music used in this video (Creative Commons Attribution):
- "Track Name" by Artist Name
  https://link-to-track
  License: CC BY 4.0
```

---

## Recommended Starting Kit

Download these to get started immediately:

1. **From Pixabay** (20 tracks):
   - Search "lofi study" - download top 10
   - Search "ambient chill" - download top 10

2. **From Mixkit** (20 tracks):
   - Browse "Lo-Fi" category - download 10
   - Browse "Ambient" category - download 10

3. **From FMA** (10 tracks):
   - Filter by CC0 license
   - Browse "Electronic > Ambient"
   - Download highly-rated tracks

This gives you ~50 tracks (~3-4 hours of music) to start producing content immediately.

---

## Legal Disclaimer

Always verify the license of any music before using it commercially. Licenses can change, and some tracks may be incorrectly categorized. When in doubt:

1. Screenshot the license at time of download
2. Keep records of where you got each track
3. Use paid services for maximum protection
4. Consider purchasing a sync license for high-value content
