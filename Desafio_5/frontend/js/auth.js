/**
 * InsureAlert — Authentication Logic (Login & Register)
 *
 * Gerencia autenticação de usuários, validação de formulários,
 * persistência de sessão e feedback visual.
 */

const AUTH_API_BASE = "";

// ═══════════════════════════════════════════════════════════
// SESSION MANAGEMENT
// ═══════════════════════════════════════════════════════════

function getSession() {
  try {
    const session = localStorage.getItem("insureAlert_session") || sessionStorage.getItem("insureAlert_session");
    return session ? JSON.parse(session) : null;
  } catch (e) {
    return null;
  }
}

function setSession(userData, remember = true) {
  const sessionStr = JSON.stringify(userData);
  if (remember) {
    localStorage.setItem("insureAlert_session", sessionStr);
  } else {
    sessionStorage.setItem("insureAlert_session", sessionStr);
    // Também grava em localStorage para compatibilidade simples de navegação
    localStorage.setItem("insureAlert_session", sessionStr);
  }
}

function clearSession() {
  localStorage.removeItem("insureAlert_session");
  sessionStorage.removeItem("insureAlert_session");
}

// ═══════════════════════════════════════════════════════════
// UI HELPERS
// ═══════════════════════════════════════════════════════════

function showMessage(text, type = "error") {
  const msgEl = document.getElementById("authMessage");
  if (!msgEl) return;

  msgEl.textContent = text;
  msgEl.className = `auth-message show ${type}`;
}

function hideMessage() {
  const msgEl = document.getElementById("authMessage");
  if (!msgEl) return;
  msgEl.className = "auth-message";
  msgEl.textContent = "";
}

function setButtonLoading(btnId, isLoading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;

  const textEl = btn.querySelector(".auth-btn-text");
  const loaderEl = btn.querySelector(".auth-btn-loader");

  btn.disabled = isLoading;

  if (textEl && loaderEl) {
    textEl.style.display = isLoading ? "none" : "inline-flex";
    loaderEl.style.display = isLoading ? "inline-flex" : "none";
  }
}

// ═══════════════════════════════════════════════════════════
// PASSWORD VISIBILITY & STRENGTH
// ═══════════════════════════════════════════════════════════

function togglePassword(inputId, toggleBtn) {
  const input = document.getElementById(inputId);
  if (!input || !toggleBtn) return;

  const isPassword = input.type === "password";
  input.type = isPassword ? "text" : "password";

  const eyeOpen = toggleBtn.querySelector(".eye-open");
  const eyeClosed = toggleBtn.querySelector(".eye-closed");

  if (eyeOpen && eyeClosed) {
    eyeOpen.style.display = isPassword ? "none" : "block";
    eyeClosed.style.display = isPassword ? "block" : "none";
  }
}

function updatePasswordStrength(password) {
  const bars = document.querySelectorAll(".strength-bar");
  const textEl = document.getElementById("strengthText");
  if (!bars.length || !textEl) return;

  if (!password) {
    bars.forEach((bar) => {
      bar.className = "strength-bar";
    });
    textEl.textContent = "";
    return;
  }

  let score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 10) score++;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  // Mapeia score (0 a 5) para 1 a 4 barras
  let strengthLevel = 0;
  let label = "";

  if (score <= 1) {
    strengthLevel = 1;
    label = "Fraca";
  } else if (score <= 3) {
    strengthLevel = 2;
    label = "Média";
  } else if (score <= 4) {
    strengthLevel = 3;
    label = "Forte";
  } else {
    strengthLevel = 4;
    label = "Excelente";
  }

  bars.forEach((bar, index) => {
    bar.className = "strength-bar";
    if (index < strengthLevel) {
      bar.classList.add("active");
      if (strengthLevel === 2) {
        bar.classList.add("medium");
      } else if (strengthLevel >= 3) {
        bar.classList.add("strong");
      }
    }
  });

  textEl.textContent = label;
}

// ═══════════════════════════════════════════════════════════
// LOGIN HANDLER
// ═══════════════════════════════════════════════════════════

async function handleLogin(event) {
  event.preventDefault();
  hideMessage();

  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const rememberInput = document.getElementById("remember");

  const email = emailInput ? emailInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";
  const remember = rememberInput ? rememberInput.checked : true;

  if (!email || !password) {
    showMessage("Por favor, preencha todos os campos.", "error");
    return;
  }

  setButtonLoading("loginBtn", true);

  try {
    let userData = null;

    // Tenta autenticar na API
    try {
      const response = await fetch(`${AUTH_API_BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (response.ok) {
        const data = await response.json();
        userData = data.user;
      } else {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Credenciais inválidas.");
      }
    } catch (apiErr) {
      // Fallback local caso backend esteja offline ou erro de rede
      if (apiErr.message.includes("Credenciais inválidas")) {
        throw apiErr;
      }

      // Validação local de contingência para conta demo
      if (email === "admin@insure.com" && password === "admin123") {
        userData = {
          id: "admin-01",
          name: "Administrador",
          email: "admin@insure.com",
          role: "admin",
          insuranceType: "todos",
        };
      } else {
        // Verifica se é um usuário registrado localmente
        const localUsers = JSON.parse(localStorage.getItem("insureAlert_registered_users") || "[]");
        const found = localUsers.find((u) => u.email.toLowerCase() === email.toLowerCase() && u.password === password);
        if (found) {
          userData = {
            id: found.id,
            name: found.name,
            email: found.email,
            role: "user",
            insuranceType: found.insuranceType,
          };
        } else {
          throw new Error("E-mail ou senha incorretos. Use a conta demo: admin@insure.com / admin123");
        }
      }
    }

    // Sucesso
    setSession(userData, remember);
    showMessage("Autenticado com sucesso! Redirecionando...", "success");

    setTimeout(() => {
      window.location.href = "/dashboard";
    }, 800);
  } catch (error) {
    showMessage(error.message || "Erro ao efetuar login. Tente novamente.", "error");
    setButtonLoading("loginBtn", false);
  }
}

// ═══════════════════════════════════════════════════════════
// REGISTER HANDLER
// ═══════════════════════════════════════════════════════════

async function handleRegister(event) {
  event.preventDefault();
  hideMessage();

  const nameInput = document.getElementById("name");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const confirmPasswordInput = document.getElementById("confirmPassword");
  const insuranceTypeInput = document.getElementById("insuranceType");
  const termsInput = document.getElementById("terms");

  const name = nameInput ? nameInput.value.trim() : "";
  const email = emailInput ? emailInput.value.trim() : "";
  const password = passwordInput ? passwordInput.value : "";
  const confirmPassword = confirmPasswordInput ? confirmPasswordInput.value : "";
  const insuranceType = insuranceTypeInput ? insuranceTypeInput.value : "";
  const terms = termsInput ? termsInput.checked : false;

  // Validações
  if (!name || !email || !password || !confirmPassword || !insuranceType) {
    showMessage("Por favor, preencha todos os campos obrigatórios.", "error");
    return;
  }

  if (password.length < 6) {
    showMessage("A senha deve conter no mínimo 6 caracteres.", "error");
    return;
  }

  if (password !== confirmPassword) {
    showMessage("As senhas informadas não coincidem.", "error");
    return;
  }

  if (!terms) {
    showMessage("Você precisa concordar com os Termos de Uso e Política de Privacidade.", "error");
    return;
  }

  setButtonLoading("registerBtn", true);

  try {
    let userData = null;

    // Tenta registrar na API
    try {
      const response = await fetch(`${AUTH_API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name,
          email,
          password,
          insurance_type: insuranceType,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        userData = data.user;
      } else {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao registrar usuário.");
      }
    } catch (apiErr) {
      if (apiErr.message.includes("já cadastrado") || apiErr.message.includes("Erro ao registrar")) {
        throw apiErr;
      }

      // Contingência local em localStorage
      const localUsers = JSON.parse(localStorage.getItem("insureAlert_registered_users") || "[]");
      const exists = localUsers.some((u) => u.email.toLowerCase() === email.toLowerCase());

      if (exists || email.toLowerCase() === "admin@insure.com") {
        throw new Error("Este e-mail já está cadastrado. Tente entrar.");
      }

      userData = {
        id: "usr-" + Date.now(),
        name,
        email,
        role: "user",
        insuranceType,
      };

      localUsers.push({
        ...userData,
        password,
      });

      localStorage.setItem("insureAlert_registered_users", JSON.stringify(localUsers));
    }

    // Registra sessão e redireciona
    setSession(userData, true);
    showMessage("Conta criada com sucesso! Redirecionando para o painel...", "success");

    setTimeout(() => {
      window.location.href = "/dashboard";
    }, 1000);
  } catch (error) {
    showMessage(error.message || "Erro ao criar conta. Verifique os dados e tente novamente.", "error");
    setButtonLoading("registerBtn", false);
  }
}

// ═══════════════════════════════════════════════════════════
// LOGOUT HANDLER
// ═══════════════════════════════════════════════════════════

async function handleLogout() {
  try {
    await fetch(`${AUTH_API_BASE}/api/auth/logout`, {
      method: "POST",
    }).catch(() => {});
  } catch (e) {
    // Silently ignore network errors during logout
  }

  clearSession();
  window.location.href = "/login";
}

// Expor globalmente para tags inline HTML
window.handleLogin = handleLogin;
window.handleRegister = handleRegister;
window.handleLogout = handleLogout;
window.togglePassword = togglePassword;
window.updatePasswordStrength = updatePasswordStrength;
