<template>
  <main class="login-page">
    <section class="login-card">
      <div class="brand">
        <img :src="logoUrl" alt="智能采购平台" />
        <div>
          <h1>智能采购助手ERP</h1>
          <p>智能采购平台</p>
        </div>
      </div>

      <div class="intro">
        <h2>欢迎登录</h2>
        <p>统一查询供应商、库存、采购订单和智能分析任务。</p>
      </div>

      <form @submit.prevent="handleSubmit">
        <label>
          <span>用户名</span>
          <input
            v-model.trim="username"
            type="text"
            autocomplete="username"
            maxlength="50"
            placeholder="请输入用户名"
            required
          />
        </label>
        <label>
          <span>密码</span>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            maxlength="128"
            placeholder="请输入密码"
            required
          />
        </label>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <button type="submit" :disabled="submitting">
          {{ submitting ? '正在登录…' : '登录平台' }}
        </button>
      </form>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { login } from '../api/auth.js'
import logoUrl from '../assets/logo.svg'

const emit = defineEmits(['authenticated'])
const username = ref('')
const password = ref('')
const submitting = ref(false)
const errorMessage = ref('')

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    const user = await login(username.value, password.value)
    password.value = ''
    emit('authenticated', user)
  } catch (error) {
    errorMessage.value = error.message || '登录失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  background:
    radial-gradient(circle at 18% 20%, rgba(14, 165, 233, 0.16), transparent 30%),
    radial-gradient(circle at 82% 78%, rgba(99, 102, 241, 0.14), transparent 32%),
    #f8fafc;
}

.login-card {
  width: min(440px, 100%);
  padding: 36px;
  border: 1px solid #e2e8f0;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.12);
}

.brand { display: flex; align-items: center; gap: 14px; }
.brand img { width: 54px; height: 54px; }
.brand h1 { margin: 0; color: #0f172a; font-size: 22px; }
.brand p { margin: 3px 0 0; color: #64748b; font-size: 14px; }
.intro { margin: 34px 0 26px; }
.intro h2 { margin: 0 0 8px; color: #0f172a; font-size: 28px; }
.intro p { margin: 0; color: #64748b; line-height: 1.7; }
form { display: grid; gap: 18px; }
label { display: grid; gap: 8px; color: #334155; font-size: 14px; font-weight: 600; }
input {
  width: 100%;
  height: 46px;
  padding: 0 14px;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  outline: none;
  color: #0f172a;
  background: white;
  transition: border-color .2s, box-shadow .2s;
}
input:focus { border-color: #0ea5e9; box-shadow: 0 0 0 4px rgba(14, 165, 233, .12); }
button {
  height: 48px;
  border: 0;
  border-radius: 12px;
  color: white;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
}
button:disabled { cursor: wait; opacity: .65; }
.error-message { margin: -4px 0 0; color: #dc2626; font-size: 14px; }
</style>
