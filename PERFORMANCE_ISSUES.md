# Performance & Behavior Issues Report

## Overview

This document identifies potential issues that can cause slow performance or unexpected behavior in the Google Maps Lead Generator.

## Performance Issues

### 1. High Number of Concurrent Tabs
**Risk**: High  
**Location**: `config.py:MAX_TABS`

Using too many tabs can:
- Cause browser instability and crashes
- Increase memory consumption significantly
- Trigger Google's anti-bot detection
- Slow down overall processing due to context switching

**Recommendation**: Keep `MAX_TABS` between 2-4 for production use.

### 2. Excessive Scroll Delay
**Risk**: Medium  
**Location**: `scraper.py:111`

The 0.8-second sleep after each scroll adds up:
- For 100 leads: ~80 seconds just waiting
- Can be optimized by detecting when no new results load

**Recommendation**: Consider reducing to 0.5s or implementing smart detection.

### 3. Stale Round Threshold
**Risk**: Low  
**Location**: `scraper.py:87`

The `max_stale=5` threshold may cause premature termination if Google loads results slowly, or unnecessary waiting if results load quickly.

**Recommendation**: Make this configurable or adaptive.

### 4. Resource Blocking Only in Phase 2
**Risk**: Low  
**Location**: `scraper.py:176`

Heavy resources are only blocked during data extraction (Phase 2), not during link collection. This is intentional but could be optimized.

### 5. No Request Caching
**Risk**: Medium  
**Location**: `scraper.py`

Every page navigation fetches all resources. No caching means repeated requests for common assets.

## Unexpected Behavior Issues

### 1. Selector Dependency on Google Maps UI
**Risk**: High  
**Location**: `scraper.py:42-56`

The scraper relies on specific CSS selectors:
- `h1.DUwDvf` - Business name
- `button[data-item-id="address"]` - Address
- `button[data-item-id^="phone:tel:"]` - Phone
- `a[data-item-id="authority"]` - Website

Google frequently changes these selectors, which will break the scraper without notice.

**Recommendation**: Implement selector fallback logic or periodic updates.

### 2. No Rate Limiting
**Risk**: High  
**Location**: `scraper.py`

No artificial delays between requests. This can:
- Trigger Google's bot detection
- Cause temporary IP blocks
- Result in CAPTCHA challenges

**Recommendation**: Add configurable delays between requests.

### 3. No Error Recovery for Partial Failures
**Risk**: Medium  
**Location**: `scraper.py:120-132`

If a single URL fails, it's silently skipped. No retry mechanism exists for transient failures (network issues, timeouts).

**Recommendation**: Implement retry logic (2-3 attempts) for failed URLs.

### 4. No Proxy Support
**Risk**: High  
**Location**: `scraper.py`

Running without proxies means:
- Single IP gets blocked easily
- No geographic targeting capability
- Higher detection risk

**Recommendation**: Add proxy rotation support.

### 5. Headless Mode Detection
**Risk**: High  
**Location**: `config.py:HEADLESS`

While Camoufox is stealthy, headless mode can still be detected. Running in headed mode (`HEADLESS=false`) is less likely to trigger detection but uses more resources.

### 6. No Session Persistence
**Risk**: Medium  
**Location**: `scraper.py:198`

Each run creates a fresh browser session. This means:
- No cookies/shared state between runs
- Cannot bypass login-based rate limits
- Every run starts from scratch

### 7. Memory Leaks from Unclosed Pages
**Risk**: Medium  
**Location**: `scraper.py:186-190`

Error handling closes pages in a try-except block, but if an exception occurs before the close attempt, pages may leak.

### 8. Queue Empty Race Condition
**Risk**: Low  
**Location**: `scraper.py:144-148`

Using `get_nowait()` with `QueueEmpty` exception is correct, but workers may not process all items if the queue isn't properly synchronized.

## Anti-Detection Concerns

### 1. No Randomization
**Risk**: High  
- Fixed viewport size (800x600)
- Consistent scroll patterns
- No random delays between actions
- Predictable behavior

**Recommendation**: Add randomization to viewport, delays, and user agents.

### 2. No User Agent Rotation
**Risk**: Medium  
**Location**: `scraper.py`

Uses default Camoufox user agent. Rotation would improve success rate.

### 3. Geographic Detection
**Risk**: Medium  
**Location**: System/Network level

Google may show different results based on the IP's geographic location. Results may vary.

## Summary

| Issue | Severity | Action Required |
|-------|----------|-----------------|
| Selector changes | High | Monitor and update |
| Rate limiting | High | Add delays |
| Proxy support | High | Add if scaling |
| No retries | Medium | Implement retry logic |
| No randomization | Medium | Add for production |
| Memory management | Medium | Improve cleanup |
| Scroll optimization | Low | Make configurable |

## Recommendations for Production Use

1. **Use proxies** - Rotate IPs to avoid blocks
2. **Add delays** - Random 1-3 second delays between requests
3. **Implement retries** - 2-3 attempts for failed URLs
4. **Monitor selectors** - Google changes UI frequently
5. **Use headed mode** - For critical scrapes, run non-headless
6. **Add logging** - Track what's working and what's not
7. **Consider CAPTCHA solving** - May be needed for large scale
