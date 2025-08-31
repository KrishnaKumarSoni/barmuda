# Barmuda Rebrand Documentation

## What Changed: Bermuda → Barmuda

This document explains the comprehensive rebrand from "Bermuda" to "Barmuda" and what must remain unchanged.

## ✅ CHANGED TO "BARMUDA"

### User-Facing Content
- Navigation bar text: "Bermuda" → "Barmuda"  
- Page titles and headers
- Footer copyright text
- All marketing copy and descriptions
- Package.json name
- Documentation references

### URLs and Domains
- bermuda.vercel.app → barmuda.vercel.app
- All test deployment URLs (bermuda-kappa.vercel.app → barmuda-kappa.vercel.app)
- Share URLs in code
- Test references and mock data

### Code References
- Comments mentioning "Bermuda"
- CSS class names and IDs where applicable
- Documentation files (CLAUDE.md, README, etc.)

## ⚠️ MUST REMAIN "BERMUDA" (Technical Infrastructure)

### Firebase Configuration
- **Firebase project ID**: `bermuda-01` 
  - This is the actual Firebase project identifier
  - Cannot be changed without creating new Firebase project
- **Service account filename**: `bermuda-01-firebase-adminsdk-fbsvc-660474f630.json`
  - This is the actual service account key file
  - Changing would break authentication
- **Database URL**: `https://bermuda-01-default-rtdb.firebaseio.com/`
  - This is the actual Realtime Database URL

### Git Repository
- Repository name: `bermuda` (on GitHub)
- Folder path: `/Users/krishna/Desktop/Dev work - 02/bermuda`
- Git history and commit messages (immutable)

## Why This Split?

1. **User Experience**: All user-facing content shows "Barmuda" for consistent branding
2. **Technical Stability**: Infrastructure identifiers remain unchanged to prevent service disruption
3. **Development Continuity**: Existing Firebase project, database, and authentication continue working

## Future Development Notes

- New developers should understand this split
- Any new Firebase resources should use "barmuda" naming if possible
- User-facing features should always use "Barmuda" branding
- Technical documentation should reference this file for clarity

## Deployment Status

- Production URL: barmuda.vercel.app (when deployment re-enabled)
- All user-facing references point to new "Barmuda" branding
- Backend infrastructure remains on "bermuda-01" Firebase project