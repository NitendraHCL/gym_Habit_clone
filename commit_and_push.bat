@echo off
cd /d C:\Users\hp\gym_habit

REM Check if git is initialized
if not exist ".git" (
    echo Initializing git repository...
    git init
    echo Git initialized.
) else (
    echo Git repository already exists.
)

echo.
echo Adding all files to git...
git add .

echo.
echo Committing changes...
git commit -m "Fix gym/partner edit endpoints and hide horizontal scrollbars - Fixed gym edit API to return {success: true} - Fixed partner edit API to return {success: true} - Hidden scrollbars on partner filter section - Hidden scrollbars on city filter section - Bumped CSS version to v11 - All admin CRUD operations now working"

echo.
echo Checking for remote repository...
git remote -v

echo.
echo If you have a remote repository configured, run:
echo git push origin main
echo.
echo Otherwise, add a remote first:
echo git remote add origin YOUR_REPO_URL
echo git push -u origin main

echo.
echo Latest commits:
git log --oneline -5

echo.
echo Done! Changes committed locally.
echo.
