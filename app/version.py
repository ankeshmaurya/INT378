import os


def build_info():
    return {
        "build_number": os.getenv("CLOUDTASK_BUILD_NUMBER", "local"),
        "git_commit": os.getenv("CLOUDTASK_GIT_COMMIT", "unknown"),
        "build_time": os.getenv("CLOUDTASK_BUILD_TIME", "unknown"),
    }
