import time

from tgalice.testing.testing_utils import make_context

from dm import WatchDM


def test_basic():
    dm = WatchDM()
    ctx = make_context('старт')
    resp = dm.respond(ctx)
    assert 'пошёл' in resp.text

    resp = dm.respond(make_context('время', prev_response=resp))
    assert '0 секунд' in resp.text

    time.sleep(2)
    resp = dm.respond(make_context('время', prev_response=resp))
    assert '2 секунды' in resp.text

    resp = dm.respond(make_context('стоп', prev_response=resp))
    assert '2 секунды' in resp.text
    assert 'остановила' in resp.text.lower()

    resp = dm.respond(make_context('время', prev_response=resp))
    assert 'не поставлен' in resp.text
