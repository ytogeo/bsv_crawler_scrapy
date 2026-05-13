from streetview_crawler.services.redis_queue import RedisPanoDownloadQueue


class FakeRedis:
    def __init__(self):
        self.sets = {}
        self.lists = {}
        self.values = {}

    def sadd(self, key, value):
        values = self.sets.setdefault(key, set())
        before = len(values)
        values.add(value)
        return 1 if len(values) > before else 0

    def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)

    def brpop(self, key, timeout=0):
        values = self.lists.get(key, [])
        if not values:
            return None
        return key, values.pop()

    def set(self, key, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def delete(self, *keys):
        for key in keys:
            self.sets.pop(key, None)
            self.lists.pop(key, None)
            self.values.pop(key, None)

    def close(self):
        pass


def test_enqueue_pano_download_once_deduplicates_by_pano_file_identity():
    fake = FakeRedis()
    queue = RedisPanoDownloadQueue(fake, "streetview", "job1")

    assert queue.enqueue_pano_download_once("job1", "pano1", "panorama", "full") is True
    assert queue.enqueue_pano_download_once("job1", "pano1", "panorama", "full") is False
    assert len(fake.lists[queue.pano_download_queue_key]) == 1


def test_metadata_done_flag():
    fake = FakeRedis()
    queue = RedisPanoDownloadQueue(fake, "streetview", "job1")

    assert queue.metadata_done() is False
    queue.set_metadata_done()
    assert queue.metadata_done() is True

