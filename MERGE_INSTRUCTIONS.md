# Инструкция: Объединение SferaAI_2 в основной репозиторий

## Проблема
`SferaAI_2` имеет свой `.git` каталог, поэтому Git видит его как вложенный репозиторий.
Изменения внутри `SferaAI_2` не попадают в основной репозиторий.

## Решение (выполните по порядку)

### Шаг 1: Удалить `.git` из SferaAI_2

```powershell
# В корне проекта (SferaTC Bot + Sfera AI/)
Remove-Item -Recurse -Force "SferaAI_2\.git"
```

### Шаг 2: Проверить статус

```powershell
git status
```

Теперь вы должны увидеть все файлы из `SferaAI_2/` как новые/измененные файлы.

### Шаг 3: Добавить всё в Git

```powershell
# Добавить все изменения
git add .

# Проверить что добавлено
git status
```

### Шаг 4: Закоммитить

```powershell
git commit -m "feat: merge SferaAI_2 into main repository

- Removed SferaAI_2/.git to convert from submodule to regular directory
- Fixed critical bugs: unified_state, duplicate get_chatgpt_response, VideoTrack
- Updated README.md and documentation
- All changes now tracked in single repository"
```

### Шаг 5: Запушить

```powershell
git push origin main
```

## Проверка успеха

После выполнения:
```powershell
git status
```

Должно показать: `On branch main, nothing to commit, working tree clean`

## Если что-то пошло не так

### Отменить всё:
```powershell
git reset --hard HEAD
git clean -fd
```

### Восстановить SferaAI_2/.git из бекапа
(если делали бекап)

---

## Быстрая команда (всё сразу)

```powershell
# ВНИМАНИЕ: Выполняйте только если уверены!
Remove-Item -Recurse -Force "SferaAI_2\.git"
git add .
git commit -m "feat: merge SferaAI_2 into main repository"
git push origin main
```
