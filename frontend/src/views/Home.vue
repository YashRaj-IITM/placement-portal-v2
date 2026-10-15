<template>
  <div class="container py-5">
    <div class="text-center bg-white rounded-3 shadow p-5 mx-auto" style="max-width: 800px">
      <img src="@/assets/logo.png" alt="logo" height="72" class="mb-3" />
      <h1 class="display-5 fw-bold">Welcome to Placement Portal</h1>
      <p class="lead text-muted mt-3">Campus placements made simple for students, companies and the placement cell.</p>
      <div class="mt-4">
        <router-link to="/login" class="btn btn-primary btn-lg m-2">Login</router-link>
        <router-link to="/register" class="btn btn-outline-success btn-lg m-2">Student Register</router-link>
        <router-link to="/register-company" class="btn btn-outline-info btn-lg m-2">Company Register</router-link>
      </div>
    </div>
  </div>
</template>

<script>
export default { name: 'HomePage' }
</script>
