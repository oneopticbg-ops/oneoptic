# Настройка стъпка по стъпка (около 30-40 минути, всичко е безплатно)

Не пиши код и не пускай нищо на компютъра си. Всичко става в браузър. След всяка част има проверка.

## 1. GitHub (хостинг на автоматизацията)
1. Влез в github.com (направи безплатен акаунт, ако нямаш) и създай ново репо, видимост **Public** (нужно е, за да е безплатно и Instagram да вижда снимките).
2. Натисни "uploading an existing file" и качи всичко от разархивираната папка `optika-bot`. Важно: папката `.github` трябва да е качена (може да е скрита - ако не я виждаш, качи двата файла от нея чрез "Add file > Create new file" с имена `.github/workflows/generate.yml` и т.н.).
3. Влез в папка `products`, качи поне 3 свои снимки на очила (JPG/PNG).

## 2. Telegram бот (за одобрение)
1. В Telegram отвори @BotFather, напиши /newbot, избери име. Ще получиш токен -> това е `TG_BOT_TOKEN`.
2. Отвори новия си бот и напиши /start.
3. В GitHub: Settings > Secrets and variables > Actions > New repository secret. Добави `TG_BOT_TOKEN`.
4. Actions > get-chat-id > Run workflow. В лога на изпълнението ще пише `TG_CHAT_ID = {число}`. Добави го като secret `TG_CHAT_ID`.

## 3. Gemini (безплатно копи)
1. Отвори aistudio.google.com/apikey, създай ключ. Добави го като secret `GEMINI_API_KEY`.

## 4. Instagram (най-трудната част)
Нужно: Instagram профилът е Business и е свързан с Facebook страница (казваш, че е така).
1. На developers.facebook.com направи приложение (тип Business), добави продукта Instagram.
2. В Graph API Explorer избери приложението и генерирай токен с разрешения: `instagram_basic`, `instagram_content_publish`, `instagram_manage_insights`, `pages_show_list`, `pages_read_engagement`, `business_management`.
3. Този токен е краткотраен. Удължи го (Access Token Debugger > Extend) до дългоживущ. Резултатът е `IG_TOKEN`.
4. `IG_USER_ID` е ID-то на Instagram профила. Намира се през Graph API Explorer със заявка `me/accounts?fields=instagram_business_account`.
5. Добави и двете като secrets.
Ако някое меню изглежда различно или се залепиш, прати ми скрийншот и ще ти кажа къде да натиснеш. Meta променя интерфейса често.

## 5. Променливи (Variables, не Secrets)
BRAND_NAME = името на оптиката. COMPETITORS = акаунти за сравнение, разделени със запетая (добави български оптики с подобен размер).

## 6. ПРОВЕРКА
Actions > check-setup > Run workflow. Ще получиш списък с ✅ и ❌ и точно какво да оправиш. Не продължавай, докато всичко не е ✅. Ще получиш и съобщение "Връзката работи" в Telegram.

## 7. Старт
Actions > generate > Run workflow. След 1-3 минути получаваш чернови в Telegram. Натискаш "Одобри" и до 20 минути постът излиза в Instagram.
Автоматично: generate върви всеки понеделник и четвъртък, publish - на всеки 20 мин.

## Ако нещо спре
Actions > отвори червеното изпълнение > копирай грешката и ми я прати.
Токенът на Instagram изтича на ~60 дни - тогава публикуването ще спре и ще ти трябва нов токен.
