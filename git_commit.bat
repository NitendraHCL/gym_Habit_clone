@echo off
cd /d C:\Users\hp\gym_habit

echo Checking git status...
git status

echo.
echo Adding all changes...
git add .

echo.
echo Committing changes...
git commit -m "Fix gym/partner edit endpoints and hide horizontal scrollbars - Fixed gym edit API to return {success: true} for consistency - Fixed partner edit API to return {success: true} for consistency - Hidden horizontal scrollbars on partner filter section (brands-grid) - Hidden horizontal scrollbars on city/location filter section (popular-areas-grid) - Bumped CSS version to v11 for cache busting - Improved UI/UX by hiding scrollbars while keeping scroll functionality - All admin panel CRUD operations now working correctly"

echo.
echo Recent commits:
git log --oneline -3

echo.
echo Done!
pause
