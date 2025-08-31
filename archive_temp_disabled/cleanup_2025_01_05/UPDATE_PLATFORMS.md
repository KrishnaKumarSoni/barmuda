# Platform Update Checklist for Barmuda

## 1. Vercel Updates ✅
- [ ] Change project name from "bermuda" to "barmuda" in Vercel dashboard
- [ ] Verify new URL: barmuda.vercel.app
- [ ] Re-enable deployment if currently disabled
- [ ] Test deployment with new URL

## 2. GitHub Updates 🐙
- [ ] Rename repository: bermuda → barmuda
- [ ] Update repository description
- [ ] Update local git remote:
  ```bash
  git remote set-url origin https://github.com/KrishnaKumarSoni/barmuda.git
  ```
- [ ] Update any GitHub Actions if needed

## 3. Firebase Updates 🔥

### Option A: Keep Existing Project (Recommended)
- [ ] Change project display name to "Barmuda" in Firebase Console
- [ ] Keep project ID as "bermuda-01" (unchangeable)
- [ ] No code changes needed

### Option B: New Firebase Project (Complex)
- [ ] Create new project "barmuda-01"
- [ ] Export/import all Firestore data
- [ ] Export/import all users
- [ ] Generate new service account key
- [ ] Update service account file in code
- [ ] Update all Firebase references in code
- [ ] Update environment variables

## 4. Update References
- [ ] Update any external documentation
- [ ] Update team wikis or notion pages
- [ ] Update any API documentation
- [ ] Update deployment guides

## 5. Final Verification
- [ ] Test Google Sign-in works
- [ ] Test form creation and saving
- [ ] Test chat functionality
- [ ] Verify all URLs redirect properly
- [ ] Check that existing data is accessible

## Notes
- Firebase project IDs cannot be changed after creation
- Vercel will handle redirects from old to new URL automatically
- GitHub will create redirects from old repository URL
- Keep the Firebase service account filename as-is unless creating new project