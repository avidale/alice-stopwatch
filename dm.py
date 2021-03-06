import os
import random
import time
from typing import Optional

import attr
import tgalice
import yaml
from tgalice.dialog import Response
from tgalice.nlu.basic_nlu import like_help
from tgalice.nlu.matchers import make_matcher_with_regex, TFIDFMatcher, TextNormalization
from tgalice.utils.serialization import Serializeable

from morph import human_duration


@attr.s
class UserState(Serializeable):
    t: Optional[float] = attr.ib(default=None)
    n_tell_time: int = attr.ib(default=0)


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
        uu = uo.get('user', {}) or uo.get('application', {})
        us = UserState(**uu)
        t = time.time()
        diff = None
        if us.t:
            diff = int(t - us.t)

        forms = self.nlu(ctx)

        response = Response(
            'привет',
            user_object={'user': us.to_dict(), 'application': us.to_dict()}
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
                us.n_tell_time = (us.n_tell_time or 0)
                if us.n_tell_time >= 3 and random.random() > 0.1:
                    response.set_rich_text(human_duration(diff))
                else:
                    response.set_rich_text(
                        f'Ваше время - {human_duration(diff)}.'
                        f'\nЧтобы запустить новый секундомер, скажите "Старт". '
                        f'Чтобы остановить этот, скажите "Стоп".'
                    )
                us.n_tell_time += 1
                response.suggests.extend(['старт', 'стоп', 'время'])
        elif 'thanks' in forms:
            response.set_rich_text(
                'Здорово, что вам нравится! '
                '\nПожалуйста, поставьте оценку навыку в каталоге.'
                '<a href="https://dialogs.yandex.ru/store/skills/a612946e-moj-sekundomer" hide=False>'
                'страница навыка'
                '</a>'
            )
        elif 'swear' in forms:
            response.set_rich_text(
                'Пожалуйста, не ругайтесь. '
                'Если вам не нравится, просто скажите "хватит", чтобы выйти из навыка. '
                'Желаю вам хорошего дня!'
            )
            response.commands.append(tgalice.COMMANDS.EXIT)
        elif 'exit' in forms or tgalice.basic_nlu.like_exit(ctx.message_text):
            response.set_rich_text('Всего хорошего! Чтобы запустить навык снова, скажите "включи навык Мой секундомер"')
            response.commands.append(tgalice.COMMANDS.EXIT)
        else:
            rt = 'Вы в навыке "Мой секундомер". Я умею засекать время!'
            if us.t:
                rt += f'\nВаше текущее время - {human_duration(diff)}.'
            rt += f'\nЧтобы запустить новый секундомер, скажите "Старт".'
            rt += f'\nЧтобы узнать, сколько времни прошло, скажите "Время".'
            rt += f'Чтобы остановить таймер, скажите "Стоп".'
            if ctx.session_is_new() or like_help(ctx.message_text or ''):
                rt += f'Чтобы выйти из навыка, скажите "Хватит".'
            response.set_rich_text(rt)
            response.suggests.extend(['старт', 'стоп', 'время', 'хватит'])

        response.user_object['user'] = us.to_dict()
        response.user_object['application'] = us.to_dict()
        return response
