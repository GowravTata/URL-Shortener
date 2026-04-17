from app.tasks.cleanup import cleanup_expired_urls

if __name__ == "__main__":
    cleanup_expired_urls.delay()