@echo off
echo ================================================================
echo GYM HABIT - PUSH TO GITHUB
echo ================================================================
echo.

cd /d C:\Users\hp\gym_habit

REM Initialize git if not already initialized
if not exist ".git" (
    echo [Step 1/6] Initializing git repository...
    git init
    echo Git initialized.
) else (
    echo [Step 1/6] Git repository already exists.
)
echo.

REM Add all changes
echo [Step 2/6] Adding all changes to git...
git add .
echo All files added.
echo.

REM Commit changes
echo [Step 3/6] Committing changes...
git commit -m "Fix gym/partner edit endpoints and hide horizontal scrollbars - Fixed gym edit API to return {success: true} - Fixed partner edit API to return {success: true} - Hidden scrollbars on partner filter section - Hidden scrollbars on city filter section - Bumped CSS version to v11 - All admin CRUD operations working - Added comprehensive E2E test suite - All modules verified and production ready"
echo.

REM Check for remote
echo [Step 4/6] Checking for GitHub remote...
git remote -v
echo.

REM Check if origin exists
git remote get-url origin >nul 2>&1
if %errorlevel% neq 0 (
    echo No GitHub remote found!
    echo.
    echo Please enter your GitHub repository URL:
    echo Example: https://github.com/username/gym_habit.git
    echo.
    set /p REPO_URL="GitHub Repository URL: "

    echo.
    echo Adding GitHub remote...
    git remote add origin !REPO_URL!
    echo Remote added successfully!
    echo.
)

REM Ensure we're on main branch
echo [Step 5/6] Setting branch to main...
git branch -M main
echo.

REM Push to GitHub
echo [Step 6/6] Pushing to GitHub...
echo.
git push -u origin main
echo.

if %errorlevel% equ 0 (
    echo ================================================================
    echo SUCCESS! Changes pushed to GitHub!
    echo ================================================================
) else (
    echo ================================================================
    echo Push failed! Please check the error above.
    echo ================================================================
    echo.
    echo Common solutions:
    echo 1. Make sure you're logged in to git
    echo    Run: git config --global user.name "Your Name"
    echo    Run: git config --global user.email "your.email@example.com"
    echo.
    echo 2. If authentication fails, you may need to use a Personal Access Token
    echo    Go to: https://github.com/settings/tokens
    echo    Generate a token and use it as your password
    echo.
    echo 3. Or try this command manually:
    echo    git push -u origin main
)

echo.
echo Latest commits:
git log --oneline -5
echo.

pause
