@echo off
echo ================================================================
echo PUSHING TO GITHUB: nikhil13dubey-star/Gym_Habit
echo ================================================================
echo.

cd /d C:\Users\hp\gym_habit

REM Initialize git if needed
if not exist ".git" (
    echo [1/7] Initializing git repository...
    git init
) else (
    echo [1/7] Git repository exists
)

REM Add all changes
echo [2/7] Adding all files...
git add .

REM Commit changes
echo [3/7] Committing changes...
git commit -m "Fix gym/partner edit endpoints and hide horizontal scrollbars - Fixed gym edit API to return {success: true} - Fixed partner edit API to return {success: true} - Hidden scrollbars on partner/city filter sections - Bumped CSS version to v11 - Added comprehensive E2E test suite - All admin CRUD operations working"

REM Remove old origin if exists
echo [4/7] Configuring GitHub remote...
git remote remove origin 2>nul

REM Add GitHub remote
echo [5/7] Adding GitHub remote...
git remote add origin https://github.com/nikhil13dubey-star/Gym_Habit.git

REM Set branch to main
echo [6/7] Setting branch to main...
git branch -M main

REM Push to GitHub
echo [7/7] Pushing to GitHub...
echo.
git push -u origin main --force
echo.

if %errorlevel% equ 0 (
    echo ================================================================
    echo SUCCESS! All changes pushed to GitHub!
    echo Repository: https://github.com/nikhil13dubey-star/Gym_Habit
    echo ================================================================
) else (
    echo ================================================================
    echo Push may have failed. Check the output above.
    echo ================================================================
    echo.
    echo If you see authentication errors, you may need to:
    echo 1. Login to GitHub in your browser
    echo 2. Use a Personal Access Token instead of password
    echo.
    echo To manually push:
    echo git push -u origin main
)

echo.
echo Recent commits:
git log --oneline -5 2>nul
echo.

pause
