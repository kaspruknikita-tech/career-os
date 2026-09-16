# Источники кейсов

Реестр источников, из которых берутся ситуации для дриллов.

**Зачем.** До этого единственным источником ситуаций были `career-data/blocks/`. Кейсы получались узнаваемыми — тренировалась память о собственном опыте, а не мышление на незнакомой вводной. Реальный вопрос с рынка точнее сгенерированного.

## Правило ротации

Перед генерацией кейса открыть этот файл, посмотреть колонку «Последний раз», взять наименее свежий подходящий источник.

- Из `blocks/` ситуация берётся **не чаще одного раза из трёх** сессий.
- `blocks/` остаются источником **проверки**: метрики, факты, формулировки. Не источником ситуаций.
- Спина кейса берётся с рынка, домен и цифры подставляются чужие — ни одного домена из раздела «Домены» в `career-data/core.md`. Иначе опора на память возвращается.
- После использования источника проставить дату и ID кейса.

## Слой 1 — банки реальных вопросов (англ)

Агрегированные отчёты живых кандидатов. Приоритетный слой для трека «TPM международные».

| Источник | URL | Что даёт | Доступ | Последний раз |
|---|---|---|---|---|
| IGotAnOffer TPM | https://igotanoffer.com/blogs/tech/technical-program-manager-interview | 50+ вопросов из 500+ отчётов Glassdoor (Amazon, Meta, Google) | 403 для бота, открывать браузером (при последней проверке) | — |
| IGotAnOffer Amazon PM | https://igotanoffer.com/blogs/tech/amazon-program-manager-interview | разрез по компании | бесплатно | — |
| IGotAnOffer Google PM | https://igotanoffer.com/blogs/tech/google-program-manager-interview | разрез по компании | бесплатно | — |
| IGotAnOffer Meta PM | https://igotanoffer.com/blogs/tech/facebook-program-manager-interview | разрез по компании | бесплатно | — |
| Exponent TPM guide | https://www.tryexponent.com/blog/technical-program-manager-interview-questions-and-answers-complete-guide | ~50 вопросов с атрибуцией компаний, program sense / behavioral / system design | бесплатно | — |
| Exponent question DB | https://www.tryexponent.com/questions?role=tpm | 264 TPM + 2006 PM вопросов | JS-страница, ботом не читается — открывать браузером | — |
| Prepfully | https://prepfully.com/interview-questions/google/product-manager | вопросы от недавних кандидатов | частично платно | — |
| Glassdoor | https://www.glassdoor.com/Interview/ | первоисточник для всех выше | нужен аккаунт | — |

## Слой 2 — ситуационные сценарии (англ)

Однострочники со сценарной рамкой. Вводные и цифры дописывать самому.

| Источник | URL | Формат | Годность | Последний раз |
|---|---|---|---|---|
| Gururo scenarios | https://gururo.com/scenario-based-interview-questions-for-project-managers/ | 5-6 сценариев: срыв срока, поздний change request, конфликт, недоработка, риск стал проблемой | средняя | — |
| Gururo Standard Chartered | https://gururo.com/senior-project-manager-case-study-in-soroco/ | полный кейс с вводными | высокая, но такой один | — |
| Welcome to the Jungle | https://www.welcometothejungle.com/en/articles/scenario-based-interview-questions-project-manager-tech | сценарные вопросы под tech PM | средняя | — |
| Indeed | https://ca.indeed.com/career-advice/interviewing/project-manager-scenario-based-interview-questions-and-answers | сценарные с шаблонными ответами | низкая | — |

## Слой 3 — русскоязычные

Приоритетный слой для трека «Delivery/PM, СНГ-рынок».

| Источник | URL | Что внутри | Годность | Последний раз |
|---|---|---|---|---|
| Хабр: 7 кейсов с собесов на PM | https://habr.com/ru/articles/943270/ | 7 реальных кейсов: премиум-подписка в банке, 15-минутная доставка, оптимизация ПВЗ, падение мотивации команды, Ферми-оценка | высокая, готовый банк | — |
| Хабр: продуктовые кейсы на собеседовании | https://habr.com/ru/articles/769078/ | типология кейсов и как решать | 403 для бота, открывать браузером | — |
| Т-Банк: PM-интервью | https://www.tbank.ru/career/it/interview/product-management/ | формат СНГ: 2-3 кейса за час | высокая | — |
| Практикум: собес на PM | https://practicum.yandex.ru/blog/sobesedovanie-na-project-menedzhera/ | типовые кейсы: спланировать запуск, переприоритизировать при отставании | средняя | — |
| psilonsk: кейс глазами интервьюера | https://psilonsk.livejournal.com/543334.html | что интервьюер проверяет кейсом | высокая, редкий угол | — |

## Слой 4 — Telegram

Не банк, а поток. Сырьё: пост про факап переформулируется в кейс.

| Канал | URL | Автор / про что |
|---|---|---|
| Об управлении проектами | https://t.me/psilonsk | кейсы и управленческий разбор |
| Нормально делай, нормально будет | https://t.me/normalno_delaj | Александра Клименко, кейсы в digital-проектах, типовые ошибки |
| Управление проектами в IT | https://t.me/dmitrii_ireshev_Agile_PMP | Дмитрий Ирешев, рук. проектного офиса СберМаркет; Agile, Scrum, SAFe, PMP |
| Fresh Product Manager | https://t.me/FreshProductGo | Сергей Колосков, продуктовые кейсы |

Подборки для расширения списка:
- https://vc.ru/life/390628-60-telegram-kanalov-i-chatov-dlya-prodzhekta
- https://pmclub.pro/articles/20-telegram-kanalov-s-vakansiyami-dlya-menedzherov/

## Слой 5 — YouTube, моки

Ценность не в вопросах, а в эталоне ответа: слышно, как звучит closing у сильного кандидата. Прямое лекарство под текущую дыру.

| Ресурс | URL |
|---|---|
| Exponent: Google TPM mock, Data Centers | https://www.youtube.com/watch?v=0rmGj6DxxkY |
| Exponent: Google EPM behavioral | https://www.youtube.com/watch?v=HhsAo8D5O_Q |
| TPM Interview Prep playlist | https://www.youtube.com/playlist?list=PLrtCHHeadkHqpCTAa20_JqYUEzK3pd3_r |
| TPM Interview Guide playlist | https://www.youtube.com/playlist?list=PLD73WK18Xz4-d1eOEPGZuZENRcCxkkb6S |

## Слой 6 — тренажёры

| Сервис | URL | Про что | Цена |
|---|---|---|---|
| Solvit | https://solvit.space/ | 3000+ вопросов с собесов, 200 задач | частично бесплатно |
| LevelForge | https://levelforge.ru/ | БА и системный анализ, кейсы | бесплатно |
| CaseCopilot | https://www.edu.fless.pro/casecopilot-ru | симулятор кейс-интервью | платно |
| GoPractice: обзор сервисов | https://gopractice.ru/skills/pm-interview-preparation/ | обзор инструментов подготовки | бесплатно |

## Слой 7 — реальный рынок

Приоритетнее всех остальных слоёв.

| Источник | Как попадает в дрилл |
|---|---|
| Транскрипты собственных интервью | `/drill debrief` — реальный вопрос точнее любого сгенерированного |
| JD с текущего поиска | `signals.md`, наполняется `resume-tailor` |
