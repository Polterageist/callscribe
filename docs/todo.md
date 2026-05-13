# TODOs

## Следующий стрим
- [X] Исправить баг E2-B1

## Backlog
- [ ] Перенести issues в Github и настроить project
- [ ] Настроить CI/CD и releases
- [ ] Добавить logging во все места где его сейчас не хватает
- [ ] Рефакторинг уже сделанной логики на async (app lifecycle + single-instance + tray wiring)
- [ ] Перевести runtime приложения на asyncio: `main()` запускает event loop, приложение живёт как async-задача
- [ ] Заменить `ThreadExecutor` на async-исполнение (или адаптер: sync handler -> `asyncio.create_task`)
- [ ] Перевести обработчики `on_start/on_stop/on_quit/on_settings` на `async def` (и обеспечить сериализацию событий)
- [ ] Сделать single-instance activation обработчик безопасным для async (bridge из thread/socket в loop через `call_soon_threadsafe`)
- [ ] Обновить интеграционные тесты запуска (`tests/integration/*`) под async-жизненный цикл без `time.sleep`-хаков
- [ ] Провести глобальный рефакторинг приложения с помощью ИИ когда MVP будет готов
- [ ] Сделать окно settings