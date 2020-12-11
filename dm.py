import os
import time
from typing import Optional

import attr
import tgalice
import yaml
from tgalice.dialog import Response
from tgalice.nlu.matchers import make_matcher_with_regex, TFIDFMatcher, TextNormalization
from tgalice.utils.serialization import Serializeable

from morph import human_duration


@attr.s
class UserState(Serializeable):
    t: Optional[float] = attr.ib(default=None)


class WatchDM(tgalice.dialog_manager.BaseDialogManager):
    def __init__(self, root_dir='data', **kwargs):
        super(WatchDM, self).__init__(**kwargs)
        with open(os.path.join(root_dir, 'intents.yaml'), 'r', encoding='utf-8') as f:
            intents = yaml.safe_load(f)

        self.intent_matcher = make_matcher_with_regex(
            base_matcher=TFIDFMatcher(text_normalization=TextNormalization.FAST_LEMMATIZE),
            intents=intents,
        )

    def nlu(self, ctx: tgalice.dialog.Context):
        intents = self.intent_matcher.aggregate_scores(ctx.message_text or '')
        forms = {k: {} for k in intents}
        if ctx.yandex and ctx.yandex.request.nlu.intents:
            forms.update({k: v.to_dict() for k, v in ctx.yandex.request.nlu.intents.items()})
        return forms

    def respond(self, ctx: tgalice.dialog.Context):
        uo = ctx.user_object or {}
        us = UserState(**uo.get('user', {}))
        t = time.time()
        diff = None
        if us.t:
            diff = int(t - us.t)

        forms = self.nlu(ctx)

        response = Response(
            'привет',
            user_object={'user': us.to_dict()}
        )

        if 'start' in forms:
            us.t = t
            response.set_rich_text(
                'Отсчёт пошёл! '
                'Скажите "Стоп", чтобы остановить его, '
                'или "Время", чтобы узнать, сколько секунд прошло. '
            )
            response.suggests = ['стоп', 'время']
        elif 'stop' in forms:
            if not us.t:
                response.set_rich_text('У вас не поставлен секундомер! Скажите "Старт", чтобы начать отсчёт.')
                response.suggests.append('старт')
            else:
                response.set_rich_text(
                    f'Остановила секундомер! '
                    f'Ваше время - {human_duration(diff)}.'
                    f'\nЧтобы запустить новый секундомер, скажите "Старт".'
                )
                response.suggests.append('старт')
                us.t = None
        elif 'time' in forms:
            if not us.t:
                response.set_rich_text('У вас не поставлен секундомер! Скажите "Старт", чтобы начать отсчёт.')
                response.suggests.append('старт')
            else:
                response.set_rich_text(
                    f'Ваше время - {human_duration(diff)}.'
                    f'\nЧтобы запустить новый секундомер, скажите "Старт". '
                    f'Чтобы остановить этот, скажите "Стоп".'
                )
                response.suggests.extend(['старт', 'стоп', 'время'])
        else:
            rt = 'Вы в навыке "Мой секундомер".'
            if us.t:
                rt += f'\nВаше текущее время - {human_duration(diff)}.'
            rt += f'\nЧтобы запустить новый секундомер, скажите "Старт".'
            rt += f'\nЧтобы узнать, сколько времни прошло, скажите "Время".'
            rt += f'Чтобы остановить таймер, скажите "Стоп".'
            response.set_rich_text(rt)
            response.suggests.extend(['старт', 'стоп', 'время'])

        response.user_object['user'] = us.to_dict()
        return response
