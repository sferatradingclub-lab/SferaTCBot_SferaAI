document.addEventListener("DOMContentLoaded", () => {
  const telegramApp = window.Telegram?.WebApp;
  const userInfoContainer = document.getElementById("user-info");

  if (!telegramApp) {
    userInfoContainer.textContent =
      "Не удалось инициализировать Telegram Web App. Попробуйте позже.";
    return;
  }

  telegramApp.ready();

  const { user } = telegramApp.initDataUnsafe ?? {};

  if (user) {
    const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ");
    const username = user.username ? `@${user.username}` : "—";

    userInfoContainer.innerHTML = `
      <p><strong>Имя:</strong> ${fullName || "—"}</p>
      <p><strong>Username:</strong> ${username}</p>
    `;
  } else {
    userInfoContainer.textContent =
      "Не удалось получить данные пользователя. Проверьте, что вы открыли приложение из Telegram.";
  }

  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.textContent = "Закрыть";
  closeButton.addEventListener("click", () => telegramApp.close());

  document.getElementById("app").appendChild(closeButton);
});
