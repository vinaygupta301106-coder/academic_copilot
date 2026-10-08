/* Academic Pathway Copilot — dashboard controller */
(() => {
  const API_BASE = "https://academic-copilot-cb4l.onrender.com/api/v1";

  function demoRoleHeaders() {
    const h = {
      "X-Demo-Role": state.demoRole || "Student",
      "X-Demo-Student-Id": String(state.currentUser?.id || "")
    };
    if (state.sessionToken) h.Authorization = `Bearer ${state.sessionToken}`;
    return h;
  }

  const DEGREE_CREDITS = 120;
  let copilotOpen = false;

  const state = {
    apiBase: API_BASE,
    currentUser: null,
    students: [],
    courses: [],
    completedCodes: new Set(),
    enrolledCodes: new Set(),
    eligibleCodes: new Set(),
    lockedCourses: [],
    activeFilter: "ready",
    search: "",
    backendOnline: false,
    sessionToken: sessionStorage.getItem("academicCopilotSessionToken") || "",
    loading: false,
    recommendations: null,
    demoRole: localStorage.getItem("academicCopilotDemoRole") || "Student",
    advisorRequests: [],
    auditTrail: [],
    selectedApprovalRequest: null,
    advisorSelectedStudentId: null,
    advisorStudentSnapshot: null
  };

  window.App = {
    API_BASE,
    state,
    escapeHtml,
    setBackendStatus,
    renderDashboard,
    getCourse,
    showToast,
    demoRoleHeaders
  };

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    lucide.createIcons();
    bindUI();
    applyDemoRole();

    /*
     * IMPORTANT:
     * Copilot must start closed on initial load and refresh.
     * It should only open when the user explicitly asks for it.
     */
    copilotOpen = false;
    minimizeCopilot();

    await loadInitialData();
    await loadAdvisorWorkflow();

    // Controlled advisor sync only; never refresh student recommendations in a loop
    window.setInterval(() => {
      if (state.demoRole !== "Student") {
        loadAdvisorWorkflow({ silent: true }).catch(() => {});
      }
    }, 15000);
  }

  function bindUI() {
    document.getElementById("user-profile-btn")?.addEventListener("click", (e) => {
      e.stopPropagation();

      const menu = document.getElementById("user-dropdown-menu");
      const btn = document.getElementById("user-profile-btn");

      menu?.classList.toggle("hidden");
      btn?.setAttribute(
        "aria-expanded",
        String(!menu?.classList.contains("hidden"))
      );
    });

    document.addEventListener("click", () => {
      document.getElementById("user-dropdown-menu")?.classList.add("hidden");
      document
        .getElementById("user-profile-btn")
        ?.setAttribute("aria-expanded", "false");
    });

    document
      .getElementById("backend-status-toggle")
      ?.addEventListener("click", checkBackendHealth);

    document
      .getElementById("course-search-input")
      ?.addEventListener("input", (e) => {
        state.search = e.target.value.toLowerCase().trim();
        applyCourseVisibility();
      });

    document.querySelectorAll(".filter-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.activeFilter = btn.dataset.filter || "all";

        document
          .querySelectorAll(".filter-pill")
          .forEach((b) => b.classList.remove("active"));

        btn.classList.add("active");
        applyCourseVisibility();
      });
    });

    document
      .getElementById("retry-btn")
      ?.addEventListener("click", loadInitialData);

    document
      .getElementById("nav-graph-btn")
      ?.addEventListener("click", () =>
        window.GraphService?.openGraph("CS401")
      );

    document
      .getElementById("trigger-visualizer-btn")
      ?.addEventListener("click", () => {
        const first =
          [...state.eligibleCodes][0] ||
          state.lockedCourses[0]?.code ||
          state.courses[0]?.code ||
          "CS401";

        window.GraphService?.openGraph(first);
      });

    document
      .getElementById("open-what-if-btn")
      ?.addEventListener("click", () => openWhatIfModal());

    document
      .getElementById("refresh-recommendations-btn")
      ?.addEventListener("click", () => loadRecommendations());

    document
      .getElementById("what-if-close-btn")
      ?.addEventListener("click", closeWhatIfModal);

    document
      .getElementById("what-if-close-confirm-btn")
      ?.addEventListener("click", closeWhatIfModal);

    document
      .getElementById("what-if-backdrop")
      ?.addEventListener("click", closeWhatIfModal);

    document
      .getElementById("what-if-run-btn")
      ?.addEventListener("click", runWhatIfSimulation);

    document
      .getElementById("what-if-action")
      ?.addEventListener("change", populateWhatIfCourses);

    document
      .getElementById("close-modal-btn")
      ?.addEventListener("click", closeGraphModal);

    document
      .getElementById("modal-close-confirm-btn")
      ?.addEventListener("click", closeGraphModal);

    document
      .querySelector("#prerequisite-modal .modal-backdrop")
      ?.addEventListener("click", closeGraphModal);

    document
      .getElementById("modal-ask-copilot-btn")
      ?.addEventListener("click", () => {
        const title =
          document.getElementById("modal-course-title")?.textContent ||
          "this course";

        closeGraphModal();

        window.Copilot?.sendQuickPrompt(
          `Explain the prerequisite chain for ${title.replace(
            "Prerequisite Knowledge Graph — ",
            ""
          )}.`
        );

        openCopilot();
      });

    document
      .getElementById("view-student-btn")
      ?.addEventListener("click", async () => {
        closeStudentMenu();
        await openStudentDetails();
      });

    document
      .getElementById("add-student-btn")
      ?.addEventListener("click", () => {
        closeStudentMenu();
        openAddStudentModal();
      });

    document
      .getElementById("close-student-modal-btn")
      ?.addEventListener("click", closeStudentModal);

    document
      .getElementById("student-modal-backdrop")
      ?.addEventListener("click", closeStudentModal);

    document
      .getElementById("student-details-close-btn")
      ?.addEventListener("click", closeStudentModal);

    document
      .getElementById("add-student-form")
      ?.addEventListener("submit", handleCreateStudent);

    document
      .getElementById("demo-role-select")
      ?.addEventListener("change", (e) => {
        state.demoRole = e.target.value;

        localStorage.setItem(
          "academicCopilotDemoRole",
          state.demoRole
        );

        window.location.reload();
      });

    /*
     * These are explicit/manual Copilot open actions.
     * Keep them.
     */
    document
      .getElementById("nav-copilot-btn")
      ?.addEventListener("click", () => openCopilot());

    document
      .getElementById("copilot-launcher-btn")
      ?.addEventListener("click", () => openCopilot());

    document
      .getElementById("copilot-minimize-btn")
      ?.addEventListener("click", () => minimizeCopilot());

    document
      .getElementById("refresh-student-overview-btn")
      ?.addEventListener("click", () =>
        loadAdvisorStudentSnapshot()
      );

    document
      .getElementById("advisor-student-select")
      ?.addEventListener("change", (e) => {
        state.advisorSelectedStudentId =
          Number(e.target.value) || null;

        loadAdvisorStudentSnapshot();
      });

    document
      .getElementById("refresh-advisor-btn")
      ?.addEventListener("click", loadAdvisorWorkflow);

    document
      .getElementById("advisor-decision-close")
      ?.addEventListener("click", closeAdvisorDecision);

    document
      .querySelector("#advisor-decision-modal .modal-backdrop")
      ?.addEventListener("click", closeAdvisorDecision);

    document
      .getElementById("advisor-approve-btn")
      ?.addEventListener("click", () =>
        decideAdvisorRequest("approve")
      );

    document
      .getElementById("advisor-reject-btn")
      ?.addEventListener("click", () =>
        decideAdvisorRequest("reject")
      );

    document
      .getElementById("advisor-changes-btn")
      ?.addEventListener("click", () =>
        decideAdvisorRequest("request changes")
      );

    document.addEventListener("click", async (e) => {
      const studentBtn = e.target.closest("[data-student-id]");

      if (studentBtn) {
        e.stopPropagation();

        const student = state.students.find(
          (s) =>
            String(s.id) === String(studentBtn.dataset.studentId)
        );

        if (student) {
          closeStudentMenu();
          await selectStudent(student);
        }

        return;
      }

      const treeBtn = e.target.closest("[data-open-tree]");

      if (treeBtn) {
        e.preventDefault();
        window.GraphService?.openGraph(treeBtn.dataset.openTree);
        return;
      }

      const whatIfBtn = e.target.closest("[data-what-if]");

      if (whatIfBtn) {
        openWhatIfModal(
          whatIfBtn.dataset.whatIf,
          whatIfBtn.dataset.whatIfAction || "take"
        );
        return;
      }

      /*
       * Recommendation "Explain" is intentionally allowed to open Copilot.
       */
      const recommendationChat = e.target.closest(
        "[data-recommendation-chat]"
      );

      if (recommendationChat) {
        const code =
          recommendationChat.dataset.recommendationChat;

        window.Copilot?.sendQuickPrompt(
          `Why is ${code} recommended for me?`
        );

        openCopilot();
        return;
      }

      const approvalBtn = e.target.closest(
        "[data-request-approval]"
      );

      if (approvalBtn) {
        await requestAdvisorApproval(
          approvalBtn.dataset.requestApproval
        );
        return;
      }

      const adjustBtn = e.target.closest(
        "[data-adjust-course]"
      );

      if (adjustBtn) {
        await adjustAdvisorCourse(
          adjustBtn.dataset.adjustCourse,
          adjustBtn.dataset.adjustStatus
        );
        return;
      }

      const reviewBtn = e.target.closest(
        "[data-review-request]"
      );

      if (reviewBtn) {
        openAdvisorDecision(
          Number(reviewBtn.dataset.reviewRequest)
        );
        return;
      }

      const enrollBtn = e.target.closest("[data-enroll]");

      if (enrollBtn) {
        await enrollCourse(enrollBtn.dataset.enroll);
      }
    });
  }

  async function loadInitialData() {
    setLoading(true);
    showCourseError(false);

    try {
      await loadStudents();

      const defaultStudent =
        state.students.find(
          (s) => String(s.id) === "1"
        ) || state.students[0];

      if (!defaultStudent) {
        throw new Error(
          "No students found. Add a student from the profile menu."
        );
      }

      await selectStudent(defaultStudent);
      await checkBackendHealth();
    } catch (err) {
      console.error(err);

      setBackendStatus(false);
      showCourseError(true, friendlyError(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadStudents() {
    const res = await fetch(
      `${API_BASE}/students/list`,
      { cache: "no-store" }
    );

    if (!res.ok) {
      throw new Error(
        `Student list request failed (${res.status})`
      );
    }

    const data = await res.json();

    state.students = Array.isArray(data)
      ? data.filter((s) => s.role === "Student")
      : [];

    renderStudentOptions();
  }

  async function ensureSession(studentId) {
    const res = await fetch(
      `${API_BASE}/auth/demo-session`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          role: state.demoRole,
          student_id:
            state.demoRole === "Student"
              ? Number(studentId)
              : null
        })
      }
    );

    if (!res.ok) {
      throw new Error(
        `Session creation failed (${res.status})`
      );
    }

    const data = await res.json();

    state.sessionToken = data.access_token;

    sessionStorage.setItem(
      "academicCopilotSessionToken",
      state.sessionToken
    );
  }

  async function selectStudent(student) {
    state.currentUser = student;
    state.completedCodes = new Set();
    state.enrolledCodes = new Set();
    state.eligibleCodes = new Set();
    state.lockedCourses = [];
    state.search = "";

    const search =
      document.getElementById("course-search-input");

    if (search) search.value = "";

    updateStudentIdentity();
    renderStudentOptions();

    await ensureSession(student.id);

    setLoading(true);
    showCourseError(false);

    try {
      const deptParam = student.department
        ? `?department=${encodeURIComponent(student.department)}`
        : "";

      const [coursesData, auditData] =
        await Promise.all([
          fetchJson(`${API_BASE}/courses/${deptParam}`),
          fetchJson(
            `${API_BASE}/students/${encodeURIComponent(
              student.id
            )}/audit`,
            { headers: demoRoleHeaders() }
          )
        ]);

      state.courses = Array.isArray(
        coursesData?.courses
      )
        ? coursesData.courses
        : [];

      applyAudit(auditData);

      await buildLockedCourses();

      renderDashboard();

      await loadRecommendations();

      setBackendStatus(true);
    } catch (err) {
      console.error(err);

      setBackendStatus(false);
      showCourseError(true, friendlyError(err));
    } finally {
      setLoading(false);
    }
  }

  function applyAudit(auditData) {
    state.completedCodes = new Set(
      (auditData?.completed_courses || [])
        .map(String)
        .map((x) => x.toUpperCase())
    );

    state.enrolledCodes = new Set(
      (auditData?.enrolled_courses || [])
        .map(String)
        .map((x) => x.toUpperCase())
    );

    const eligible = Array.isArray(
      auditData?.eligible_courses
    )
      ? auditData.eligible_courses
      : [];

    state.eligibleCodes = new Set(
      eligible.map((c) =>
        String(c.code).toUpperCase()
      )
    );
  }

  async function buildLockedCourses() {
    const completed = state.completedCodes;
    const eligible = state.eligibleCodes;

    const candidates = state.courses.filter(
      (c) =>
        c?.code &&
        !completed.has(
          String(c.code).toUpperCase()
        ) &&
        !state.enrolledCodes.has(
          String(c.code).toUpperCase()
        ) &&
        !eligible.has(
          String(c.code).toUpperCase()
        )
    );

    const results = await Promise.all(
      candidates.map(async (course) => {
        try {
          const data = await fetchJson(
            `${API_BASE}/courses/${encodeURIComponent(
              course.code
            )}/prerequisites`
          );

          const prereqs = Array.isArray(
            data?.prerequisites
          )
            ? data.prerequisites
                .map(String)
                .map((x) => x.toUpperCase())
            : [];

          const missing = prereqs.filter(
            (code) => !completed.has(code)
          );

          if (missing.length > 0) {
            return {
              ...course,
              prerequisites: prereqs,
              missing_prerequisites: missing
            };
          }

          return null;
        } catch {
          return {
            ...course,
            prerequisites: [],
            missing_prerequisites: [],
            prerequisiteLookupFailed: true
          };
        }
      })
    );

    state.lockedCourses =
      results.filter(Boolean);
  }

  async function loadAuditOnly() {
    if (!state.currentUser) return;

    const data = await fetchJson(
      `${API_BASE}/students/${encodeURIComponent(
        state.currentUser.id
      )}/audit`,
      {
        headers: demoRoleHeaders()
      }
    );

    applyAudit(data);

    await buildLockedCourses();

    renderDashboard();

    renderStudentOptions();

    await loadRecommendations();

    await loadAdvisorWorkflow();

    applyDemoRole();
  }

  async function enrollCourse(code) {
    if (
      !state.currentUser ||
      !code ||
      state.demoRole !== "Student"
    ) {
      return;
    }

    const upper = String(code).toUpperCase();

    if (state.enrolledCodes.has(upper)) {
      showToast(
        `${upper} is already enrolled.`,
        "info"
      );
      return;
    }

    if (state.completedCodes.has(upper)) {
      showToast(
        `${upper} is already completed.`,
        "info"
      );
      return;
    }

    const button = document.querySelector(
      `[data-enroll="${CSS.escape(code)}"]`
    );

    if (button) {
      button.disabled = true;
      button.dataset.originalText =
        button.textContent;
      button.textContent = "Requesting...";
    }

    try {
      const res = await fetch(
        `${API_BASE}/students/enroll`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...demoRoleHeaders()
          },
          body: JSON.stringify({
            user_id: Number(
              state.currentUser.id
            ),
            course_code: code
          })
        }
      );

      if (!res.ok) {
        let detail =
          "Unable to request enrollment approval.";

        try {
          detail =
            (await res.json())?.detail ||
            detail;
        } catch {}

        throw new Error(detail);
      }

      const data = await res.json();

      showToast(
        data.message ||
          `Advisor approval requested for ${upper}.`,
        data.status === "PENDING"
          ? "success"
          : "info"
      );

      await loadAuditOnly();
    } catch (err) {
      console.error(err);

      showToast(
        err?.message ||
          `Unable to request enrollment for ${upper}.`,
        "error"
      );
    } finally {
      const current =
        document.querySelector(
          `[data-enroll="${CSS.escape(code)}"]`
        );

      if (current) {
        current.disabled = false;
        current.textContent =
          current.dataset.originalText ||
          "Enroll in Course";
      }
    }
  }

  async function loadRecommendations() {
    if (!state.currentUser) return;

    /*
     * Recommendation refresh is allowed to update the dashboard,
     * but it must not change Copilot visibility.
     */
    const loading = document.getElementById(
      "recommendation-loading"
    );

    const content = document.getElementById(
      "recommendation-content"
    );

    const error = document.getElementById(
      "recommendation-error"
    );

    const errorText = document.getElementById(
      "recommendation-error-text"
    );

    loading?.classList.remove("hidden");
    error?.classList.add("hidden");

    try {
      const data = await fetchJson(
        `${API_BASE}/copilot/recommendations/${encodeURIComponent(
          state.currentUser.id
        )}`,
        {
          headers: demoRoleHeaders()
        }
      );

      state.recommendations = data;

      renderRecommendations(data);

      content?.classList.remove("hidden");

      setText(
        "recommendation-user-code",
        state.currentUser.id
      );
    } catch (err) {
      console.error(err);

      state.recommendations = null;

      content?.classList.add("hidden");

      if (errorText) {
        errorText.textContent =
          err?.message ||
          "Unable to calculate recommendations.";
      }

      error?.classList.remove("hidden");
    } finally {
      loading?.classList.add("hidden");
      lucide.createIcons();
    }
  }

  function renderRecommendations(data) {
    const list = document.getElementById(
      "recommendation-list"
    );

    const blockers = document.getElementById(
      "blocker-list"
    );

    const blockerSection =
      document.getElementById(
        "blocker-section"
      );

    const recommendations = Array.isArray(
      data?.recommendations
    )
      ? data.recommendations
      : [];

    const pathwayBlockers = Array.isArray(
      data?.pathway_blockers
    )
      ? data.pathway_blockers
      : [];

    const nextActions = Array.isArray(
      data?.next_actions
    )
      ? data.next_actions
      : [];

    setText(
      "recommendation-count",
      recommendations.length
        ? `${recommendations.length} ranked option${
            recommendations.length === 1
              ? ""
              : "s"
          }`
        : "No eligible options"
    );

    if (recommendations.length) {
      list.innerHTML = recommendations
        .slice(0, 6)
        .map(
          (r, index) => `
        <article class="recommendation-card ${
          index === 0 ? "featured" : ""
        }">
          <div class="recommendation-rank">
            #${escapeHtml(r.rank)}
            <span>${escapeHtml(
              r.priority || "Option"
            )}</span>
          </div>

          <div class="recommendation-main">
            <div class="flex min-w-0 items-start justify-between gap-3">
              <div class="min-w-0">
                <div class="course-code">
                  ${escapeHtml(r.code)}
                </div>
                <h4>${escapeHtml(r.name)}</h4>
              </div>

              <span class="course-credits">
                ${Number(r.credits || 0)} Credits
              </span>
            </div>

            <div class="recommendation-meta">
              <span>
                Semester ${escapeHtml(
                  r.semester ?? "—"
                )}
              </span>

              <span>
                ${
                  r.unlock_count
                    ? `Unlocks ${r.unlock_count} more`
                    : "No immediate unlocks"
                }
              </span>
            </div>

            <div class="recommendation-reasons">
              ${(r.reasons || [])
                .map(
                  (x) =>
                    `<span>
                      <i data-lucide="check" class="h-3 w-3"></i>
                      ${escapeHtml(x)}
                    </span>`
                )
                .join("")}
            </div>

            <div class="course-actions">
              <button
                type="button"
                class="primary-btn"
                data-enroll="${escapeAttr(r.code)}"
              >
                <i
                  data-lucide="plus"
                  class="h-3.5 w-3.5"
                ></i>
                Enroll
              </button>

              <button
                type="button"
                class="secondary-btn"
                data-what-if="${escapeAttr(r.code)}"
                data-what-if-action="take"
              >
                <i
                  data-lucide="flask-conical"
                  class="h-3.5 w-3.5"
                ></i>
                Simulate
              </button>

              <button
                type="button"
                class="secondary-btn"
                data-recommendation-chat="${escapeAttr(
                  r.code
                )}"
              >
                <i
                  data-lucide="message-circle"
                  class="h-3.5 w-3.5"
                ></i>
                Explain
              </button>

              ${
                state.demoRole === "Student"
                  ? `
              <button
                type="button"
                class="secondary-btn"
                data-request-approval="${escapeAttr(
                  r.code
                )}"
              >
                <i
                  data-lucide="user-check"
                  class="h-3.5 w-3.5"
                ></i>
                Request approval
              </button>
              `
                  : ""
              }
            </div>
          </div>
        </article>`
        )
        .join("");
    } else if (nextActions.length) {
      list.innerHTML = nextActions
        .map(
          (a) => `
        <article class="recommendation-card blocker-action">
          <div class="recommendation-rank">
            <span>Pathway action</span>
          </div>

          <div class="recommendation-main">
            <div class="course-code">
              ${escapeHtml(a.code)}
            </div>

            <h4>${escapeHtml(a.name)}</h4>

            <p>${escapeHtml(a.reason)}</p>

            <div class="recommendation-reasons">
              <span>
                <i
                  data-lucide="lock"
                  class="h-3 w-3"
                ></i>
                Missing:
                ${escapeHtml(
                  (a.missing_prerequisites || [])
                    .join(", ") ||
                    "prerequisite data"
                )}
              </span>
            </div>
          </div>
        </article>`
        )
        .join("");
    } else {
      list.innerHTML = emptyInline(
        "No immediate recommendation is available from the current curriculum state."
      );
    }

    if (pathwayBlockers.length) {
      blockerSection?.classList.remove(
        "hidden"
      );

      blockers.innerHTML = pathwayBlockers
        .slice(0, 6)
        .map(
          (b) => `
        <article class="blocker-card">
          <div class="flex items-start justify-between gap-3">
            <div>
              <span class="course-code text-sm">
                ${escapeHtml(b.code)}
              </span>

              <h4>${escapeHtml(b.name)}</h4>
            </div>

            <span
              class="status-badge ${
                b.eligible_now
                  ? "ready"
                  : "locked"
              }"
            >
              ${
                b.eligible_now
                  ? "Eligible now"
                  : "Blocked"
              }
            </span>
          </div>

          <p>${escapeHtml(b.reason)}</p>

          <div class="blocker-courses">
            ${(b.blocked_course_codes || [])
              .map(
                (code) =>
                  `<span>${escapeHtml(
                    code
                  )}</span>`
              )
              .join("")}
          </div>

          ${
            b.eligible_now
              ? `
          <button
            type="button"
            class="secondary-btn mt-3 w-full"
            data-what-if="${escapeAttr(
              b.code
            )}"
            data-what-if-action="take"
          >
            <i
              data-lucide="flask-conical"
              class="h-3.5 w-3.5"
            ></i>
            Simulate ${escapeHtml(
              b.code
            )}
          </button>
          `
              : ""
          }
        </article>`
        )
        .join("");
    } else {
      blockerSection?.classList.add(
        "hidden"
      );
    }

    const methodology = Array.isArray(
      data?.methodology
    )
      ? data.methodology.join(" ")
      : "Recommendations use verified curriculum and student data.";

    setText(
      "recommendation-methodology",
      methodology
    );

    lucide.createIcons();
  }

  function applyDemoRole() {
    const role =
      state.demoRole || "Student";

    const select = document.getElementById(
      "demo-role-select"
    );

    if (select) select.value = role;

    const staff = role !== "Student";

    document
      .querySelectorAll("[data-student-only]")
      .forEach((el) => {
        if (el.id === "copilot") return;
        el.classList.toggle(
          "hidden",
          staff
        );
      });

    const copilotPanel = document.getElementById("copilot");
    const copilotLauncher = document.getElementById("copilot-launcher");
    if (staff) {
      copilotPanel?.classList.add("hidden");
      copilotLauncher?.classList.add("hidden");
    } else {
      if (copilotOpen) {
        copilotPanel?.classList.remove("hidden");
        copilotLauncher?.classList.add("hidden");
      } else {
        copilotPanel?.classList.add("hidden");
        copilotLauncher?.classList.remove("hidden");
      }
    }

    document
      .getElementById(
        "student-approval-view"
      )
      ?.classList.toggle(
        "hidden",
        staff
      );

    document
      .getElementById(
        "advisor-review-view"
      )
      ?.classList.toggle(
        "hidden",
        !staff
      );

    document
      .getElementById(
        "advisor-student-view"
      )
      ?.classList.toggle(
        "hidden",
        !staff
      );

    document
      .getElementById("audit-view")
      ?.classList.remove("hidden");

    const badge = document.getElementById(
      "workflow-role-badge"
    );

    if (badge) {
      badge.className =
        `workflow-role-badge ${role.toLowerCase()}`;

      badge.innerHTML = `
        <i
          data-lucide="${
            role === "Student"
              ? "user-round"
              : role === "Advisor"
              ? "user-check"
              : "shield"
          }"
          class="h-3.5 w-3.5"
        ></i>
        ${role} view
      `;
    }

    lucide.createIcons();
  }

  /*
   * Explicit Copilot open action.
   * This function is NOT automatically called by
   * recommendation/dashboard refreshes.
   */
  function openCopilot() {
    if (state.demoRole !== "Student") return;
    copilotOpen = true;

    const panel =
      document.getElementById("copilot");

    panel?.classList.remove("hidden");

    document
      .getElementById(
        "copilot-launcher-wrap"
      )
      ?.classList.add("hidden");

    document
      .getElementById(
        "copilot-launcher"
      )
      ?.classList.add("hidden");

    setTimeout(
      () =>
        document
          .getElementById(
            "copilot-input"
          )
          ?.focus(),
      80
    );

    lucide.createIcons();
  }

  /*
   * Copilot minimized/closed state.
   * Called during normal dashboard refreshes so
   * Recommendation Dashboard never forces it open.
   */
  function minimizeCopilot() {
    copilotOpen = false;

    document
      .getElementById("copilot")
      ?.classList.add("hidden");

    if (state.demoRole === "Student") {
      document
        .getElementById("copilot-launcher")
        ?.classList.remove("hidden");
    }
  }

  async function requestAdvisorApproval(code) {
    if (state.demoRole !== "Student") {
      showToast(
        "Switch to Student view to submit an approval request.",
        "error"
      );
      return;
    }

    const reason =
      `Requesting advisor review for ${code} based on the current pathway recommendation.`;

    try {
      const data = await fetchJson(
        `${API_BASE}/advisor/requests`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...demoRoleHeaders()
          },
          body: JSON.stringify({
            student_id: Number(
              state.currentUser.id
            ),
            course_code: code,
            reason,
            actor_role: "Student"
          })
        }
      );

      showToast(
        data.message ||
          `Advisor approval requested for ${code}.`,
        data.status === "EXISTS"
          ? "info"
          : "success"
      );

      await loadAdvisorWorkflow();
    } catch (err) {
      showToast(
        err?.message ||
          "Unable to submit advisor request.",
        "error"
      );
    }
  }

  async function adjustAdvisorCourse(
    code,
    currentStatus
  ) {
    if (
      !state.currentUser ||
      !state.advisorSelectedStudentId ||
      state.demoRole === "Student"
    ) {
      return;
    }

    const action =
      currentStatus === "completed"
        ? "adjust"
        : "remove";

    const message =
      currentStatus === "completed"
        ? `This will remove ${code} from the completed academic record and affect eligibility. Continue?`
        : `Remove ${code} from the student's current enrollment?`;

    if (!window.confirm(message))
      return;

    const reason = window.prompt(
      "Enter the reason for this academic record change:",
      currentStatus === "completed"
        ? "Academic record correction"
        : "Enrollment adjustment"
    );

    if (
      !reason ||
      reason.trim().length < 3
    ) {
      showToast(
        "A reason of at least 3 characters is required.",
        "error"
      );
      return;
    }

    try {
      const data = await fetchJson(
        `${API_BASE}/students/${encodeURIComponent(
          state.advisorSelectedStudentId
        )}/course-records/adjust`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...demoRoleHeaders()
          },
          body: JSON.stringify({
            course_code: code,
            action: "remove",
            reason: reason.trim()
          })
        }
      );

      showToast(
        data.message ||
          `${code} ${action} completed.`,
        "success"
      );

      await loadAdvisorWorkflow();
    } catch (err) {
      showToast(
        err?.message ||
          `Unable to adjust ${code}.`,
        "error"
      );
    }
  }

  async function loadAdvisorWorkflow({
    silent = false
  } = {}) {
    if (!state.currentUser) return;

    try {
      const [requests, audit] =
        await Promise.all([
          fetchJson(
            `${API_BASE}/advisor/requests?${
              state.demoRole === "Student"
                ? `student_id=${encodeURIComponent(
                    state.currentUser.id
                  )}`
                : ""
            }`,
            {
              headers: demoRoleHeaders()
            }
          ),

          fetchJson(
            `${API_BASE}/advisor/audit-trail?${
              state.demoRole === "Student"
                ? `student_id=${encodeURIComponent(
                    state.currentUser.id
                  )}&`
                : ""
            }limit=30`,
            {
              headers: demoRoleHeaders()
            }
          )
        ]);

      state.advisorRequests =
        Array.isArray(requests)
          ? requests
          : [];

      state.auditTrail =
        Array.isArray(audit)
          ? audit
          : [];

      renderAdvisorWorkflow();

      if (
        state.demoRole !== "Student"
      ) {
        await loadAdvisorStudentDirectory();
      }
    } catch (err) {
      console.error(err);

      if (!silent) {
        showToast(
          err?.message ||
            "Unable to load advisor workflow.",
          "error"
        );
      }
    }
  }

  async function loadAdvisorStudentDirectory() {
    const select = document.getElementById(
      "advisor-student-select"
    );

    if (!select) return;

    const students = Array.isArray(
      state.students
    )
      ? state.students
      : [];

    select.innerHTML = students.length
      ? students
          .map(
            (s) => `
          <option value="${escapeAttr(
            s.id
          )}">
            ${escapeHtml(
              s.name
            )} • #${escapeHtml(
              s.id
            )} • Sem ${escapeHtml(
              s.semester ?? "—"
            )}
          </option>`
          )
          .join("")
      : `<option value="">No students available</option>`;

    if (
      !state.advisorSelectedStudentId ||
      !students.some(
        (s) =>
          Number(s.id) ===
          Number(
            state.advisorSelectedStudentId
          )
      )
    ) {
      state.advisorSelectedStudentId =
        Number(students[0]?.id) || null;
    }

    if (
      state.advisorSelectedStudentId
    ) {
      select.value = String(
        state.advisorSelectedStudentId
      );
    }

    await loadAdvisorStudentSnapshot();
  }

  async function loadAdvisorStudentSnapshot() {
    if (
      state.demoRole === "Student" ||
      !state.advisorSelectedStudentId
    ) {
      return;
    }

    const loading =
      document.getElementById(
        "advisor-student-loading"
      );

    const box =
      document.getElementById(
        "advisor-student-overview"
      );

    loading?.classList.remove(
      "hidden"
    );

    try {
      const [
        student,
        audit,
        coursesData
      ] = await Promise.all([
        fetchJson(
          `${API_BASE}/students/${encodeURIComponent(
            state.advisorSelectedStudentId
          )}`,
          {
            headers:
              demoRoleHeaders()
          }
        ),

        fetchJson(
          `${API_BASE}/students/${encodeURIComponent(
            state.advisorSelectedStudentId
          )}/audit`,
          {
            headers:
              demoRoleHeaders()
          }
        ),

        fetchJson(
          `${API_BASE}/courses/`
        )
      ]);

      const courses = Array.isArray(
        coursesData?.courses
      )
        ? coursesData.courses
        : [];

      const completed = new Set(
        (audit?.completed_courses || [])
          .map((x) =>
            String(x).toUpperCase()
          )
      );

      const enrolled = new Set(
        (audit?.enrolled_courses || [])
          .map((x) =>
            String(x).toUpperCase()
          )
      );

      const completedCourses =
        courses.filter((c) =>
          completed.has(
            String(c.code).toUpperCase()
          )
        );

      const enrolledCourses =
        courses.filter((c) =>
          enrolled.has(
            String(c.code).toUpperCase()
          )
        );

      const credits =
        completedCourses.reduce(
          (sum, c) =>
            sum +
            Number(c.credits || 0),
          0
        );

      const eligible = Array.isArray(
        audit?.eligible_courses
      )
        ? audit.eligible_courses
        : [];

      const eligibleSet = new Set(
        eligible.map((c) =>
          String(c.code).toUpperCase()
        )
      );

      const locked =
        courses.filter(
          (c) =>
            c?.code &&
            !completed.has(
              String(c.code).toUpperCase()
            ) &&
            !enrolled.has(
              String(c.code).toUpperCase()
            ) &&
            !eligibleSet.has(
              String(c.code).toUpperCase()
            )
        );

      state.advisorStudentSnapshot = {
        student,
        audit,
        credits
      };

      if (box) {
        box.innerHTML = `
          <div class="advisor-student-header">
            <div>
              <div class="course-code">
                ${escapeHtml(
                  student.name
                )}
              </div>

              <p>
                ${escapeHtml(
                  student.department ||
                    "—"
                )}
                •
                ${escapeHtml(
                  student.track ||
                    "—"
                )}
              </p>
            </div>

            <span class="workflow-role-badge student">
              <i
                data-lucide="user-round"
                class="h-3.5 w-3.5"
              ></i>
              Student #${escapeHtml(
                student.id
              )}
            </span>
          </div>

          <div class="advisor-overview-stats">
            <div class="workflow-stat">
              <span>Semester</span>
              <strong>
                ${escapeHtml(
                  student.semester ??
                    "—"
                )}/8
              </strong>
            </div>

            <div class="workflow-stat">
              <span>Credits</span>
              <strong>
                ${credits}/120
              </strong>
            </div>

            <div class="workflow-stat">
              <span>Completed</span>
              <strong>
                ${completedCourses.length}
              </strong>
            </div>

            <div class="workflow-stat">
              <span>Eligible</span>
              <strong>
                ${eligible.length}
              </strong>
            </div>

            <div class="workflow-stat">
              <span>Locked</span>
              <strong>
                ${locked.length}
              </strong>
            </div>
          </div>

          <div class="advisor-course-columns">
            <div class="advisor-course-box">
              <h4>Enrolled</h4>

              <div class="advisor-course-manage-list">
                ${
                  enrolledCourses.length
                    ? enrolledCourses
                        .map(
                          (c) => `
                        <div class="advisor-course-manage-row">
                          <div>
                            <strong>
                              ${escapeHtml(
                                c.code
                              )}
                            </strong>

                            <span>
                              ${escapeHtml(
                                c.name ||
                                  "Course"
                              )}
                              •
                              ${Number(
                                c.credits ||
                                  0
                              )}
                              cr
                            </span>
                          </div>

                          <button
                            type="button"
                            class="secondary-btn danger-btn"
                            data-adjust-course="${escapeAttr(
                              c.code
                            )}"
                            data-adjust-status="enrolled"
                          >
                            <i
                              data-lucide="user-minus"
                              class="h-3.5 w-3.5"
                            ></i>
                            Remove
                          </button>
                        </div>
                      `
                        )
                        .join("")
                    : "<span>None</span>"
                }
              </div>
            </div>

            <div class="advisor-course-box">
              <h4>Completed</h4>

              <div class="advisor-course-manage-list">
                ${
                  completedCourses.length
                    ? completedCourses
                        .map(
                          (c) => `
                        <div class="advisor-course-manage-row">
                          <div>
                            <strong>
                              ${escapeHtml(
                                c.code
                              )}
                            </strong>

                            <span>
                              ${escapeHtml(
                                c.name ||
                                  "Course"
                              )}
                              •
                              ${Number(
                                c.credits ||
                                  0
                              )}
                              cr
                            </span>
                          </div>

                          <button
                            type="button"
                            class="secondary-btn"
                            data-adjust-course="${escapeAttr(
                              c.code
                            )}"
                            data-adjust-status="completed"
                          >
                            <i
                              data-lucide="file-pen-line"
                              class="h-3.5 w-3.5"
                            ></i>
                            Adjust
                          </button>
                        </div>
                      `
                        )
                        .join("")
                    : "<span>None</span>"
                }
              </div>
            </div>

            <div class="advisor-course-box">
              <h4>Currently Eligible</h4>

              <div class="advisor-course-chips">
                ${
                  eligible.length
                    ? eligible
                        .slice(0, 12)
                        .map(
                          (c) =>
                            `<span>${escapeHtml(
                              c.code
                            )}</span>`
                        )
                        .join("")
                    : "<span>None</span>"
                }
              </div>
            </div>
          </div>
        `;
      }

      lucide.createIcons();
    } catch (err) {
      if (box) {
        box.innerHTML = emptyInline(
          err?.message ||
            "Unable to load student academic snapshot."
        );
      }
    } finally {
      loading?.classList.add(
        "hidden"
      );
    }
  }

  function renderAdvisorWorkflow() {
    const role = state.demoRole;
    const requests =
      state.advisorRequests || [];

    const studentList =
      document.getElementById(
        "student-request-list"
      );

    const advisorList =
      document.getElementById(
        "advisor-request-list"
      );

    if (role === "Student") {
      setText(
        "student-request-count",
        requests.length
      );

      if (studentList) {
        studentList.innerHTML =
          requests.length
            ? requests
                .slice(0, 8)
                .map(
                  (r) => `
                  <article class="approval-card">
                    <div>
                      <div class="course-code">
                        ${escapeHtml(
                          r.course_code
                        )}
                      </div>

                      <h4>
                        ${escapeHtml(
                          r.student_name ||
                            "Current student"
                        )}

                        <span
                          class="approval-status ${String(
                            r.status
                          )
                            .toLowerCase()
                            .replace(
                              /\s+/g,
                              "-"
                            )}"
                        >
                          ${escapeHtml(
                            r.status
                          )}
                        </span>
                      </h4>

                      <p>
                        ${escapeHtml(
                          r.reason ||
                            "Advisor review requested."
                        )}
                      </p>
                    </div>

                    <div class="approval-meta">
                      <span>
                        ${escapeHtml(
                          r.created_at ||
                            ""
                        )}
                      </span>

                      ${
                        r.advisor_note
                          ? `<span>
                              Note:
                              ${escapeHtml(
                                r.advisor_note
                              )}
                            </span>`
                          : ""
                      }
                    </div>
                  </article>
                `
                )
                .join("")
            : emptyInline(
                "No advisor approval requests yet. Use “Advisor approval” on a recommendation to submit one."
              );
      }
    } else {
      const pending =
        requests.filter(
          (r) => r.status === "Pending"
        ).length;

      const approved =
        requests.filter(
          (r) => r.status === "Approved"
        ).length;

      const rejected =
        requests.filter(
          (r) => r.status === "Rejected"
        ).length;

      const changes =
        requests.filter(
          (r) =>
            r.status ===
            "Changes Requested"
        ).length;

      setText(
        "approval-pending-count",
        pending
      );

      setText(
        "approval-approved-count",
        approved
      );

      setText(
        "approval-rejected-count",
        rejected
      );

      setText(
        "approval-changes-count",
        changes
      );

      if (advisorList) {
        advisorList.innerHTML =
          requests.length
            ? requests
                .slice(0, 12)
                .map(
                  (r) => `
                  <article
                    class="approval-card ${
                      r.status === "Pending"
                        ? "pending"
                        : ""
                    }"
                  >
                    <div>
                      <div class="flex items-center gap-2">
                        <div class="course-code">
                          ${escapeHtml(
                            r.course_code
                          )}
                        </div>

                        <span
                          class="approval-status ${String(
                            r.status
                          )
                            .toLowerCase()
                            .replace(
                              /\s+/g,
                              "-"
                            )}"
                        >
                          ${escapeHtml(
                            r.status
                          )}
                        </span>
                      </div>

                      <h4>
                        ${escapeHtml(
                          r.student_name ||
                            "Student"
                        )}

                        <span class="text-slate-600">
                          #${escapeHtml(
                            r.student_id
                          )}
                        </span>
                      </h4>

                      <p>
                        ${escapeHtml(
                          r.reason ||
                            "No reason supplied."
                        )}
                      </p>
                    </div>

                    <div class="approval-actions">
                      ${
                        r.status === "Pending"
                          ? `
                      <button
                        type="button"
                        class="primary-btn"
                        data-review-request="${escapeAttr(
                          r.id
                        )}"
                      >
                        <i
                          data-lucide="clipboard-check"
                          class="h-3.5 w-3.5"
                        ></i>
                        Review
                      </button>
                      `
                          : `
                      <span class="text-[9px] text-slate-500">
                        Reviewed by
                        ${escapeHtml(
                          r.reviewed_by ||
                            "Advisor"
                        )}
                      </span>
                      `
                      }
                    </div>
                  </article>
                `
                )
                .join("")
            : emptyInline(
                "No approval requests are waiting for review."
              );
      }
    }

    const auditList =
      document.getElementById(
        "audit-trail-list"
      );

    const audit =
      state.auditTrail || [];

    setText(
      "audit-event-count",
      `${audit.length} event${
        audit.length === 1
          ? ""
          : "s"
      }`
    );

    if (auditList) {
      auditList.innerHTML =
        audit.length
          ? audit
              .slice(0, 15)
              .map(
                (a) => `
                <div class="audit-event">
                  <div class="audit-event-icon">
                    <i
                      data-lucide="history"
                      class="h-3.5 w-3.5"
                    ></i>
                  </div>

                  <div class="min-w-0 flex-1">
                    <div class="flex flex-wrap items-center gap-2">
                      <strong>
                        ${escapeHtml(
                          a.action
                        )}
                      </strong>

                      <span>
                        ${escapeHtml(
                          a.actor_role
                        )}
                        •
                        ${escapeHtml(
                          a.actor_name
                        )}
                      </span>
                    </div>

                    <p>
                      ${escapeHtml(
                        a.details ||
                          (a.course_code
                            ? `Course ${a.course_code}`
                            : "System event")
                      )}
                    </p>

                    <time>
                      ${escapeHtml(
                        a.created_at ||
                          ""
                      )}
                    </time>
                  </div>
                </div>
              `
              )
              .join("")
          : emptyInline(
              "No audit events recorded yet."
            );
    }

    lucide.createIcons();
  }

  async function openAdvisorDecision(
    requestId
  ) {
    const request =
      (state.advisorRequests || [])
        .find(
          (r) =>
            Number(r.id) ===
            Number(requestId)
        );

    if (!request) return;

    state.selectedApprovalRequest =
      request;

    setText(
      "advisor-decision-title",
      `Review ${request.course_code}`
    );

    setText(
      "advisor-decision-subtitle",
      `${request.student_name || "Student"} • Request #${request.id}`
    );

    const box =
      document.getElementById(
        "advisor-decision-details"
      );

    if (box) {
      box.innerHTML = `
        <div class="detail-field">
          <span>Student</span>
          <strong>
            ${escapeHtml(
              request.student_name
            )}
            (#${escapeHtml(
              request.student_id
            )})
          </strong>
        </div>

        <div class="detail-field">
          <span>Course</span>
          <strong>
            ${escapeHtml(
              request.course_code
            )}
          </strong>
        </div>

        <div class="detail-field">
          <span>Status</span>
          <strong>
            ${escapeHtml(
              request.status
            )}
          </strong>
        </div>

        <div class="detail-field sm:col-span-2">
          <span>Student reason</span>
          <strong>
            ${escapeHtml(
              request.reason || "—"
            )}
          </strong>
        </div>
      `;
    }

    const note =
      document.getElementById(
        "advisor-note-input"
      );

    if (note) {
      note.value =
        request.advisor_note || "";
    }

    document
      .getElementById(
        "advisor-decision-modal"
      )
      ?.classList.remove("hidden");

    lucide.createIcons();
  }

  function closeAdvisorDecision() {
    document
      .getElementById(
        "advisor-decision-modal"
      )
      ?.classList.add("hidden");

    state.selectedApprovalRequest =
      null;
  }

  async function decideAdvisorRequest(
    decision
  ) {
    const request =
      state.selectedApprovalRequest;

    if (!request) return;

    const note =
      document
        .getElementById(
          "advisor-note-input"
        )
        ?.value.trim() || "";

    const buttons = [
      "advisor-approve-btn",
      "advisor-reject-btn",
      "advisor-changes-btn"
    ]
      .map((id) =>
        document.getElementById(id)
      )
      .filter(Boolean);

    buttons.forEach(
      (b) => (b.disabled = true)
    );

    try {
      const data = await fetchJson(
        `${API_BASE}/advisor/requests/${encodeURIComponent(
          request.id
        )}/decision`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
            ...demoRoleHeaders()
          },
          body: JSON.stringify({
            decision,
            note,
            actor_role:
              state.demoRole,
            actor_name:
              state.demoRole ===
              "Coordinator"
                ? "Demo Coordinator"
                : "Demo Advisor"
          })
        }
      );

      closeAdvisorDecision();

      showToast(
        data.message ||
          "Advisor decision saved.",
        "success"
      );

      await loadAdvisorWorkflow();
    } catch (err) {
      showToast(
        err?.message ||
          "Unable to save advisor decision.",
        "error"
      );
    } finally {
      buttons.forEach(
        (b) => (b.disabled = false)
      );
    }
  }

  function renderDashboard() {
    const ready =
      state.courses.filter(
        (c) =>
          state.eligibleCodes.has(
            String(c.code).toUpperCase()
          ) &&
          !state.completedCodes.has(
            String(c.code).toUpperCase()
          ) &&
          !state.enrolledCodes.has(
            String(c.code).toUpperCase()
          )
      );

    const locked =
      state.lockedCourses;

    const completed =
      state.courses.filter((c) =>
        state.completedCodes.has(
          String(c.code).toUpperCase()
        )
      );

    const enrolled =
      state.courses.filter((c) =>
        state.enrolledCodes.has(
          String(c.code).toUpperCase()
        )
      );

    renderReady(ready);
    renderEnrolled(enrolled);
    renderLocked(locked);
    renderCompleted(completed);

    const total =
      state.courses.length;

    const completedCredits =
      completed.reduce(
        (sum, c) =>
          sum +
          Number(c.credits || 0),
        0
      );

    const remainingCredits = Math.max(DEGREE_CREDITS - completedCredits, 0);

    const progress = Math.min(
      100,
      Math.round(
        (completedCredits /
          DEGREE_CREDITS) *
          100
      )
    );

    setText(
      "count-completed",
      completed.length
    );

    setText(
      "count-eligible",
      ready.length
    );

    setText(
      "count-locked",
      locked.length
    );

    setText(
      "credits-stat",
      completedCredits
    );

    setText(
      "credits-earned",
      completedCredits
    );

    setText(
      "credits-required",
      DEGREE_CREDITS
    );

    setText(
      "credits-percent",
      `${progress}% of degree target`
    );

    // Progressive Degree Requirement Audit section
    setText(
      "summary-credits-completed",
      completedCredits
    );

    setText(
      "summary-credits-remaining",
      remainingCredits
    );

    setText(
      "summary-progress-percent",
      `${progress}%`
    );

    setText(
      "degree-dept-badge",
      state.currentUser?.department || state.currentUser?.track || "Curriculum"
    );

    renderSemesterCreditsBreakdown(completed);

    setText(
      "progress-text",
      `${progress}%`
    );

    setText(
      "progress-caption",
      "Live persistent audit"
    );

    const ring =
      document.getElementById(
        "progress-ring"
      );

    if (ring) {
      ring.style.setProperty(
        "--progress",
        `${progress}%`
      );
    }

    setText(
      "filter-all-count",
      total
    );

    setText(
      "filter-ready-count",
      ready.length
    );

    setText(
      "filter-locked-count",
      locked.length
    );

    setText(
      "filter-completed-count",
      completed.length
    );

    setText(
      "ready-summary",
      `${ready.length} available now`
    );

    setText(
      "locked-summary",
      `${locked.length} prerequisite blockers`
    );

    setText(
      "audit-user-code",
      state.currentUser?.id ?? 1
    );

    document
      .getElementById(
        "course-loading"
      )
      ?.classList.add("hidden");

    document
      .getElementById(
        "course-content"
      )
      ?.classList.remove("hidden");

    applyCourseVisibility();

    lucide.createIcons();
  }

  function renderSemesterCreditsBreakdown(completedCourses) {
    const grid = document.getElementById("semester-credits-grid");
    if (!grid) return;

    const completedCodes = new Set(
      (completedCourses || []).map((c) => String(c.code).toUpperCase())
    );

    const semesterMap = {};
    for (let sem = 1; sem <= 8; sem++) {
      semesterMap[sem] = { totalCredits: 0, completedCredits: 0, totalCourses: 0, completedCourses: 0 };
    }

    state.courses.forEach((c) => {
      const sem = Number(c.semester) || 1;
      if (semesterMap[sem]) {
        const credits = Number(c.credits || 0);
        semesterMap[sem].totalCredits += credits;
        semesterMap[sem].totalCourses += 1;
        if (completedCodes.has(String(c.code).toUpperCase())) {
          semesterMap[sem].completedCredits += credits;
          semesterMap[sem].completedCourses += 1;
        }
      }
    });

    grid.innerHTML = [1, 2, 3, 4, 5, 6, 7, 8].map((sem) => {
      const data = semesterMap[sem] || { totalCredits: 15, completedCredits: 0 };
      const total = data.totalCredits || 15;
      const comp = data.completedCredits;
      const isComplete = comp >= total && comp > 0;
      const isCurrent = Number(state.currentUser?.semester || 1) === sem;

      return `
        <div class="rounded-xl border ${isComplete ? 'border-emerald-400/30 bg-emerald-500/10' : isCurrent ? 'border-cyan-400/40 bg-cyan-500/10' : 'border-white/10 bg-black/30'} p-3 flex flex-col justify-between">
          <div class="flex items-center justify-between text-[11px] font-semibold">
            <span class="${isCurrent ? 'text-cyan-300' : isComplete ? 'text-emerald-300' : 'text-slate-400'}">Sem ${sem}</span>
            ${isComplete ? '<span class="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>' : isCurrent ? '<span class="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse"></span>' : ''}
          </div>
          <div class="mt-2">
            <div class="text-sm font-bold text-white">${comp} <span class="text-[10px] font-normal text-slate-400">/ ${total} cr</span></div>
            <div class="text-[9px] text-slate-400 mt-0.5">${isComplete ? 'Completed' : isCurrent ? 'Current' : `${Math.max(total - comp, 0)} cr left`}</div>
          </div>
        </div>
      `;
    }).join("");
  }

  function renderReady(courses) {
    const container =
      document.getElementById(
        "ready-list"
      );

    if (!container) return;

    if (!courses.length) {
      container.innerHTML =
        emptyInline(
          "No courses are currently eligible."
        );
      return;
    }

    container.innerHTML =
      courses
        .map(
          (course) => `
          <article
            class="course-card ready"
            data-course-card
            data-state="ready"
            data-course-code="${escapeAttr(
              course.code
            )}"
            data-course-title="${escapeAttr(
              course.name || ""
            )}"
          >
            <div class="absolute left-0 right-0 top-0 h-[2px] bg-gradient-to-r from-cyan-400 via-indigo-500 to-transparent"></div>

            <div class="course-top">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <span class="course-code">
                    ${escapeHtml(
                      course.code
                    )}
                  </span>

                  <span class="badge badge-slate text-[10px]">
                    Sem ${Number(course.semester || 1)}
                  </span>

                  <span class="status-badge ready">
                    <i
                      data-lucide="check"
                      class="h-3 w-3"
                    ></i>
                    Eligible
                  </span>
                </div>

                <h4 class="course-name">
                  ${escapeHtml(
                    course.name ||
                      "Course"
                  )}
                </h4>
              </div>

              <span class="course-credits">
                ${Number(
                  course.credits || 0
                )} Credits
              </span>
            </div>

            <p class="course-desc">
              ${escapeHtml(
                course.description ||
                  "Eligible according to the current prerequisite audit."
              )}
            </p>

            <div class="course-meta">
              <div class="course-meta-row">
                <span>Prerequisites</span>
                <span class="text-emerald-300">
                  Satisfied
                </span>
              </div>

              <div class="course-meta-row">
                <span>Minimum grade</span>
                <span>
                  ${escapeHtml(
                    course.min_grade ??
                      "—"
                  )}
                </span>
              </div>
            </div>

            <div class="course-actions">
              <button
                type="button"
                class="primary-btn"
                data-enroll="${escapeAttr(
                  course.code
                )}"
              >
                <i
                  data-lucide="plus"
                  class="h-3.5 w-3.5"
                ></i>
                Enroll in Course
              </button>

              <button
                type="button"
                class="secondary-btn"
                data-what-if="${escapeAttr(
                  course.code
                )}"
                data-what-if-action="take"
              >
                <i
                  data-lucide="flask-conical"
                  class="h-3.5 w-3.5 text-violet-300"
                ></i>
                Simulate
              </button>

              <button
                type="button"
                class="secondary-btn"
                data-open-tree="${escapeAttr(
                  course.code
                )}"
              >
                <i
                  data-lucide="git-merge"
                  class="h-3.5 w-3.5 text-cyan-300"
                ></i>
                Tree
              </button>
            </div>
          </article>
        `
        )
        .join("");
  }

  function renderLocked(courses) {
    const container =
      document.getElementById(
        "locked-list"
      );

    if (!container) return;

    if (!courses.length) {
      container.innerHTML =
        emptyInline(
          "No prerequisite blockers detected."
        );
      return;
    }

    container.innerHTML = courses
      .map((course) => {
        const missing =
          course.missing_prerequisites ||
          [];

        const requirementText =
          course.prerequisiteLookupFailed
            ? "Prerequisite details could not be retrieved."
            : missing.length
            ? `Requires ${missing.join(
                ", "
              )}`
            : "Eligibility is not currently returned by the audit endpoint.";

        return `
          <article
            class="course-card locked"
            data-course-card
            data-state="locked"
            data-course-code="${escapeAttr(
              course.code
            )}"
            data-course-title="${escapeAttr(
              course.name || ""
            )}"
          >
            <div class="course-top">
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <span class="course-code">
                    ${escapeHtml(
                      course.code
                    )}
                  </span>

                  <span class="badge badge-slate text-[10px]">
                    Sem ${Number(course.semester || 1)}
                  </span>

                  <span class="status-badge locked">
                    <i
                      data-lucide="lock"
                      class="h-3 w-3"
                    ></i>
                    Locked
                  </span>
                </div>

                <h4 class="course-name">
                  ${escapeHtml(
                    course.name ||
                      "Course"
                  )}
                </h4>
              </div>

              <span class="course-credits">
                ${Number(
                  course.credits || 0
                )} Credits
              </span>
            </div>

            <div class="missing-box">
              <div class="flex items-start gap-2">
                <i
                  data-lucide="alert-triangle"
                  class="mt-0.5 h-3.5 w-3.5 shrink-0"
                ></i>

                <span>
                  ${escapeHtml(
                    requirementText
                  )}
                </span>
              </div>
            </div>

            <div class="course-meta">
              <div class="course-meta-row">
                <span>Pending track</span>

                <span class="text-amber-300">
                  ${
                    missing.length ||
                    "Unknown"
                  }
                  prerequisite${
                    missing.length === 1
                      ? ""
                      : "s"
                  }
                </span>
              </div>

              <div class="course-meta-row">
                <span>Minimum grade</span>

                <span>
                  ${escapeHtml(
                    course.min_grade ??
                      "—"
                  )}
                </span>
              </div>
            </div>

            <div class="course-actions">
              <button
                type="button"
                class="secondary-btn"
                data-what-if="${escapeAttr(
                  course.code
                )}"
                data-what-if-action="take"
              >
                <i
                  data-lucide="flask-conical"
                  class="h-3.5 w-3.5 text-violet-300"
                ></i>
                Simulate
              </button>

              <button
                type="button"
                class="secondary-btn"
                data-open-tree="${escapeAttr(
                  course.code
                )}"
              >
                <i
                  data-lucide="route"
                  class="h-3.5 w-3.5 text-amber-300"
                ></i>
                View Requirements & Graph
              </button>
            </div>
          </article>
        `;
      })
      .join("");
  }

  function renderEnrolled(courses) {
    const container =
      document.getElementById(
        "enrolled-list"
      );

    if (!container) return;

    if (!courses.length) {
      container.innerHTML =
        emptyInline(
          "No courses are currently enrolled."
        );
      return;
    }

    container.innerHTML =
      courses
        .map(
          (course) => `
          <article
            class="completed-card"
            data-course-card
            data-state="enrolled"
            data-course-code="${escapeAttr(
              course.code
            )}"
            data-course-title="${escapeAttr(
              course.name || ""
            )}"
          >
            <div class="completed-code">
              ◉ ${escapeHtml(
                course.code
              )}
            </div>

            <div
              class="completed-name"
              title="${escapeAttr(
                course.name || ""
              )}"
            >
              ${escapeHtml(
                course.name ||
                  "Course"
              )}
            </div>

            <div class="completed-meta">
              ${Number(
                course.credits || 0
              )} cr • Enrolled
            </div>

            <span class="status-badge ready">
              Advisor approved
            </span>
          </article>
        `
        )
        .join("");
  }

  function renderCompleted(courses) {
    const container =
      document.getElementById(
        "completed-list"
      );

    if (!container) return;

    if (!courses.length) {
      container.innerHTML =
        emptyInline(
          "No completed courses were returned for this student."
        );
      return;
    }

    container.innerHTML =
      courses
        .map(
          (course) => `
          <article
            class="completed-card"
            data-course-card
            data-state="completed"
            data-course-code="${escapeAttr(
              course.code
            )}"
            data-course-title="${escapeAttr(
              course.name || ""
            )}"
          >
            <div class="completed-code">
              ✓ ${escapeHtml(
                course.code
              )}
            </div>

            <div
              class="completed-name"
              title="${escapeAttr(
                course.name || ""
              )}"
            >
              ${escapeHtml(
                course.name ||
                  "Course"
              )}
            </div>

            <div class="completed-meta">
              ${Number(
                course.credits || 0
              )} cr
            </div>

            <button
              type="button"
              class="mini-action"
              data-what-if="${escapeAttr(
                course.code
              )}"
              data-what-if-action="skip"
            >
              <i
                data-lucide="git-branch-minus"
                class="h-3 w-3"
              ></i>
              What if I skip it?
            </button>
          </article>
        `
        )
        .join("");
  }

  function applyCourseVisibility() {
    const cards = [
      ...document.querySelectorAll(
        "[data-course-card]"
      )
    ];

    const groups = [
      ...document.querySelectorAll(
        ".course-group-section"
      )
    ];

    cards.forEach((card) => {
      const stateMatch =
        state.activeFilter === "all" ||
        card.dataset.state ===
          state.activeFilter;

      const haystack = `
        ${card.dataset.courseCode || ""}
        ${card.dataset.courseTitle || ""}
      `.toLowerCase();

      const searchMatch =
        !state.search ||
        haystack.includes(
          state.search
        );

      card.classList.toggle(
        "hidden",
        !(stateMatch && searchMatch)
      );
    });

    groups.forEach((group) => {
      const visibleCards =
        group.querySelectorAll(
          "[data-course-card]:not(.hidden)"
        ).length;

      const filterMatch =
        state.activeFilter === "all" ||
        group.dataset.group ===
          state.activeFilter;

      group.classList.toggle(
        "hidden",
        !filterMatch ||
          visibleCards === 0
      );
    });

    const anyVisible = cards.some(
      (c) =>
        !c.classList.contains(
          "hidden"
        )
    );

    document
      .getElementById(
        "no-course-results"
      )
      ?.classList.toggle(
        "hidden",
        anyVisible
      );
  }

  function openWhatIfModal(
    preselectedCode = "",
    action = "take"
  ) {
    const modal =
      document.getElementById(
        "what-if-modal"
      );

    if (!modal) return;

    modal.classList.remove(
      "hidden"
    );

    const actionEl =
      document.getElementById(
        "what-if-action"
      );

    if (actionEl) {
      actionEl.value =
        action === "skip"
          ? "skip"
          : "take";
    }

    populateWhatIfCourses(
      preselectedCode
    );

    clearWhatIfResult();

    lucide.createIcons();
  }

  function closeWhatIfModal() {
    document
      .getElementById(
        "what-if-modal"
      )
      ?.classList.add("hidden");
  }

  function populateWhatIfCourses(
    preselectedCode = ""
  ) {
    const select =
      document.getElementById(
        "what-if-course"
      );

    const action =
      document.getElementById(
        "what-if-action"
      )?.value || "take";

    if (!select) return;

    const completed =
      state.completedCodes;

    const courses = [
      ...state.courses
    ]
      .filter((c) => c?.code)
      .sort((a, b) =>
        String(a.code).localeCompare(
          String(b.code)
        )
      );

    const allowed =
      action === "skip"
        ? courses.filter((c) =>
            completed.has(
              String(
                c.code
              ).toUpperCase()
            )
          )
        : courses.filter((c) =>
            !completed.has(
              String(
                c.code
              ).toUpperCase()
            )
          );

    select.innerHTML =
      `<option value="">Select a course...</option>` +
      allowed
        .map(
          (c) =>
            `<option value="${escapeAttr(
              c.code
            )}">
              ${escapeHtml(
                c.code
              )} — ${escapeHtml(
                c.name ||
                  "Course"
              )}
            </option>`
        )
        .join("");

    if (
      preselectedCode &&
      allowed.some(
        (c) =>
          String(c.code).toUpperCase() ===
          String(
            preselectedCode
          ).toUpperCase()
      )
    ) {
      select.value =
        String(
          preselectedCode
        ).toUpperCase();
    }

    clearWhatIfResult();
  }

  function clearWhatIfResult() {
    document
      .getElementById(
        "what-if-result"
      )
      ?.classList.add("hidden");

    document
      .getElementById(
        "what-if-error"
      )
      ?.classList.add("hidden");

    document
      .getElementById(
        "what-if-loading"
      )
      ?.classList.add("hidden");
  }

  async function runWhatIfSimulation() {
    if (!state.currentUser)
      return;

    const action =
      document.getElementById(
        "what-if-action"
      )?.value || "take";

    const code =
      document.getElementById(
        "what-if-course"
      )?.value || "";

    const result =
      document.getElementById(
        "what-if-result"
      );

    const loading =
      document.getElementById(
        "what-if-loading"
      );

    const error =
      document.getElementById(
        "what-if-error"
      );

    const errorText =
      document.getElementById(
        "what-if-error-text"
      );

    if (!code) {
      if (errorText) {
        errorText.textContent =
          "Select a course before running the simulation.";
      }

      error?.classList.remove(
        "hidden"
      );

      return;
    }

    result?.classList.add(
      "hidden"
    );

    error?.classList.add(
      "hidden"
    );

    loading?.classList.remove(
      "hidden"
    );

    const button =
      document.getElementById(
        "what-if-run-btn"
      );

    if (button)
      button.disabled = true;

    try {
      const res = await fetch(
        `${API_BASE}/copilot/what-if`,
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
            ...demoRoleHeaders()
          },
          body: JSON.stringify({
            user_id: Number(
              state.currentUser.id
            ),
            action,
            course_codes: [code]
          })
        }
      );

      if (!res.ok) {
        let detail =
          "Simulation failed.";

        try {
          detail =
            (await res.json())
              ?.detail ||
            detail;
        } catch {}

        throw new Error(detail);
      }

      const data =
        await res.json();

      renderWhatIfResult(data);
    } catch (err) {
      if (errorText) {
        errorText.textContent =
          err?.message ||
          "Unable to run the simulation.";
      }

      error?.classList.remove(
        "hidden"
      );
    } finally {
      loading?.classList.add(
        "hidden"
      );

      if (button)
        button.disabled = false;
    }
  }

  function renderWhatIfResult(data) {
    const el =
      document.getElementById(
        "what-if-result"
      );

    if (!el) return;

    const impact =
      data.impact || {};

    const simulated =
      data.simulated || {};

    const baseline =
      data.baseline || {};

    const fmt = (codes) =>
      Array.isArray(codes) &&
      codes.length
        ? codes.join(", ")
        : "None";

    const requested =
      Array.isArray(
        data.requested_courses
      )
        ? data.requested_courses
        : [];

    const blocked =
      Array.isArray(
        data.blocked_courses
      )
        ? data.blocked_courses
        : [];

    const actionText =
      data.action === "skip"
        ? "Skip / remove"
        : "Take / complete";

    const delta = Number(
      impact.credit_delta || 0
    );

    const deltaText = `${
      delta > 0 ? "+" : ""
    }${delta.toFixed(0)} cr`;

    el.innerHTML = `
      <div class="mb-3 flex items-center justify-between gap-3">
        <div>
          <div class="text-[10px] font-bold uppercase tracking-[0.12em] text-violet-300">
            Simulation result
          </div>

          <h3 class="mt-1 font-display text-sm font-bold">
            ${escapeHtml(
              actionText
            )}
            ${escapeHtml(
              requested
                .map(
                  (c) => c.code
                )
                .join(", ")
            )}
          </h3>
        </div>

        <span
          class="status-badge ${
            blocked.length
              ? "locked"
              : "ready"
          }"
        >
          ${
            blocked.length
              ? "Blocked"
              : "Simulated"
          }
        </span>
      </div>

      <div class="what-if-summary">
        <div class="what-if-stat">
          <span>Credits</span>

          <strong>
            ${Number(
              simulated.credits ||
                0
            ).toFixed(0)}

            <small class="text-xs text-slate-500">
              (${deltaText})
            </small>
          </strong>
        </div>

        <div class="what-if-stat">
          <span>Eligible after</span>

          <strong>
            ${
              Array.isArray(
                simulated.eligible_courses
              )
                ? simulated
                    .eligible_courses
                    .length
                : 0
            }
          </strong>
        </div>

        <div class="what-if-stat">
          <span>Database changed</span>

          <strong class="text-emerald-300">
            No
          </strong>
        </div>
      </div>

      <div class="what-if-impact">
        <div class="what-if-impact-card">
          <h4>Newly eligible</h4>

          <div class="what-if-course-list">
            ${chips(
              impact.newly_eligible
            )}
          </div>
        </div>

        <div class="what-if-impact-card">
          <h4>
            Newly locked / no longer eligible
          </h4>

          <div class="what-if-course-list">
            ${chips([
              ...(impact.newly_locked ||
                []),
              ...(impact.no_longer_eligible ||
                [])
            ])}
          </div>
        </div>

        ${
          blocked.length
            ? `
        <div class="what-if-impact-card">
          <h4>
            Scenario blocker
          </h4>

          <p>
            ${blocked
              .map(
                (c) =>
                  `<strong>${escapeHtml(
                    c.code
                  )}</strong> — missing ${escapeHtml(
                    (
                      c.missing_prerequisites ||
                      []
                    ).join(", ") ||
                      "prerequisites"
                  )}`
              )
              .join("<br>")}
          </p>
        </div>
        `
            : ""
        }

        <div class="what-if-impact-card">
          <h4>
            Verified basis
          </h4>

          <p>
            Baseline completed courses:
            ${escapeHtml(
              fmt(
                baseline.completed_courses
              )
            )}.
            The simulation uses the Neo4j curriculum graph and MySQL completion record and does not write to the database.
          </p>
        </div>
      </div>
    `;

    el.classList.remove(
      "hidden"
    );

    lucide.createIcons();
  }

  function chips(codes) {
    if (
      !Array.isArray(codes) ||
      !codes.length
    ) {
      return `<span class="text-[10px] text-slate-500">No change</span>`;
    }

    return codes
      .map(
        (code) =>
          `<span class="what-if-course-chip">
            ${escapeHtml(
              code
            )}
          </span>`
      )
      .join("");
  }

  async function checkBackendHealth() {
    try {
      const res = await fetch(
        `${API_BASE}/students/${encodeURIComponent(
          state.currentUser?.id || 1
        )}/audit`,
        {
          cache: "no-store",
          headers:
            demoRoleHeaders()
        }
      );

      if (!res.ok)
        throw new Error();

      setBackendStatus(true);

      return true;
    } catch {
      setBackendStatus(false);

      return false;
    }
  }

  function setBackendStatus(
    online
  ) {
    state.backendOnline =
      online;

    const pill =
      document.getElementById(
        "backend-status-toggle"
      );

    const dot =
      document.getElementById(
        "backend-dot"
      );

    const text =
      document.getElementById(
        "backend-status-text"
      );

    const footer =
      document.getElementById(
        "footer-fastapi"
      );

    pill?.classList.toggle(
      "online",
      online
    );

    pill?.classList.toggle(
      "offline",
      !online
    );

    if (dot) {
      dot.className =
        `status-dot ${
          online
            ? "bg-emerald-400 animate-pulse"
            : "bg-rose-400"
        }`;
    }

    if (text) {
      text.textContent =
        online
          ? "Backend Live"
          : "Backend Offline";
    }

    if (footer) {
      footer.textContent =
        online
          ? "Online"
          : "Offline";
    }
  }

  function updateStudentIdentity() {
    const student =
      state.currentUser || {};

    const deptText = student.department || student.track || "AI & Data Science";

    setText(
      "display-user-name",
      student.name ||
        "Student"
    );

    setText(
      "hero-user-name",
      student.name ||
        "Student"
    );

    setText(
      "display-user-track",
      deptText
    );

    setText(
      "summary-track",
      `Track: ${deptText}`
    );

    setText(
      "summary-semester",
      `Semester ${student.semester || 1} of 8`
    );

    setText(
      "degree-dept-badge",
      deptText
    );

    setText(
      "audit-user-code",
      student.id ?? 1
    );

    const initials = (
      student.name ||
      "ST"
    )
      .split(/\s+/)
      .map((x) => x[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

    setText(
      "avatar-initials",
      initials
    );
  }

  function renderStudentOptions() {
    const container =
      document.getElementById(
        "student-options"
      );

    if (!container) return;

    container.innerHTML =
      state.students
        .map(
          (student) => `
          <button
            type="button"
            class="student-option ${
              String(student.id) ===
              String(
                state.currentUser?.id
              )
                ? "current"
                : ""
            }"
            data-student-id="${escapeAttr(
              student.id
            )}"
          >
            <span>
              <span class="block text-[11px] font-semibold">
                ${escapeHtml(
                  student.name
                )}
              </span>

              <small>
                ${escapeHtml(
                  student.track ||
                    student.department ||
                    "Student"
                )}
              </small>
            </span>

            <small>
              ID:
              ${escapeHtml(
                student.id
              )}
            </small>
          </button>
        `
        )
        .join("");
  }

  async function openStudentDetails() {
    if (!state.currentUser)
      return;

    try {
      const student =
        await fetchJson(
          `${API_BASE}/students/${encodeURIComponent(
            state.currentUser.id
          )}`,
          {
            headers:
              demoRoleHeaders()
          }
        );

      setText(
        "details-name",
        student.name
      );

      setText(
        "details-id",
        student.id
      );

      setText(
        "details-email",
        student.email ||
          "Not provided"
      );

      setText(
        "details-department",
        student.department ||
          "—"
      );

      setText(
        "details-track",
        student.track ||
          "—"
      );

      setText(
        "details-semester",
        student.semester ||
          "—"
      );

      setText(
        "details-role",
        student.role ||
          "Student"
      );

      setText(
        "details-subjects",
        `${student.department || student.track || "Curriculum"} curriculum (semester-based)`
      );

      setText(
        "details-completed",
        (
          student.completed_courses ||
          []
        ).join(", ") ||
          "None"
      );

      document
        .getElementById(
          "student-details-modal"
        )
        ?.classList.remove(
          "hidden"
        );
    } catch (err) {
      showToast(
        err?.message ||
          "Unable to load student details.",
        "error"
      );
    }
  }

  async function openAddStudentModal() {
    document
      .getElementById(
        "add-student-form"
      )
      ?.reset();

    const deptSelect = document.getElementById("student-department-select");
    const trackInput = document.getElementById("student-track-input");
    const semSelect = document.getElementById("student-semester-input");

    if (deptSelect && trackInput) {
      trackInput.value = deptSelect.value;
    }

    document
      .getElementById(
        "add-student-modal"
      )
      ?.classList.remove(
        "hidden"
      );

    await populateAddStudentCourses();

    if (deptSelect && !deptSelect._hasChangeListener) {
      deptSelect._hasChangeListener = true;
      deptSelect.addEventListener("change", async () => {
        if (trackInput) trackInput.value = deptSelect.value;
        await populateAddStudentCourses();
      });
    }

    if (semSelect && !semSelect._hasChangeListener) {
      semSelect._hasChangeListener = true;
      semSelect.addEventListener("change", async () => {
        await populateAddStudentCourses();
      });
    }

    setTimeout(
      () =>
        document
          .getElementById(
            "student-name-input"
          )
          ?.focus(),
      50
    );
  }

  async function populateAddStudentCourses() {
    const picker = document.getElementById("student-courses-picker");
    const deptSelect = document.getElementById("student-department-select");
    const semSelect = document.getElementById("student-semester-input");
    const countEl = document.getElementById("selected-completed-count");
    if (!picker) return;

    const dept = deptSelect?.value || "AI & Data Science";
    const curSem = Number(semSelect?.value || 1);

    picker.innerHTML = '<div class="col-span-2 py-3 text-center text-xs text-slate-500">Loading curriculum courses...</div>';

    try {
      const data = await fetchJson(`${API_BASE}/courses/curriculum?department=${encodeURIComponent(dept)}`);
      const semCourses = data?.curriculum || {};

      const eligibleList = [];
      for (let s = 1; s <= 8; s++) {
        const list = semCourses[s] || [];
        list.forEach((c) => {
          eligibleList.push({ ...c, semester: s });
        });
      }

      if (!eligibleList.length) {
        picker.innerHTML = '<div class="col-span-2 py-3 text-center text-xs text-slate-500">No courses defined for this department.</div>';
        return;
      }

      picker.innerHTML = eligibleList.map((c) => {
        // Pre-check courses if their semester is strictly before the selected current semester
        const isPreceding = c.semester < curSem;
        return `
          <label class="flex items-center gap-2 p-1.5 rounded hover:bg-white/5 cursor-pointer text-slate-300">
            <input type="checkbox" class="add-student-course-cb accent-cyan-400" value="${escapeAttr(c.code)}" data-credits="${Number(c.credits || 0)}" ${isPreceding ? "checked" : ""} />
            <span class="font-mono text-cyan-300 font-bold">${escapeHtml(c.code)}</span>
            <span class="truncate text-[11px]">${escapeHtml(c.name)}</span>
            <span class="text-[10px] text-slate-500 ml-auto whitespace-nowrap">Sem ${c.semester} • ${c.credits}cr</span>
          </label>
        `;
      }).join("");

      const updateCount = () => {
        const checked = picker.querySelectorAll(".add-student-course-cb:checked");
        let totalCredits = 0;
        checked.forEach((cb) => {
          totalCredits += Number(cb.dataset.credits || 0);
        });
        if (countEl) {
          countEl.textContent = `${checked.length} selected (${totalCredits} credits)`;
        }
      };

      picker.querySelectorAll(".add-student-course-cb").forEach((cb) => {
        cb.addEventListener("change", updateCount);
      });
      updateCount();
    } catch (err) {
      console.error(err);
      picker.innerHTML = '<div class="col-span-2 py-3 text-center text-xs text-rose-400">Failed to load courses.</div>';
    }
  }

  async function handleCreateStudent(
    e
  ) {
    e.preventDefault();

    const submit =
      document.getElementById(
        "create-student-btn"
      );

    if (submit) {
      submit.disabled = true;
      submit.textContent =
        "Creating...";
    }

    const picker = document.getElementById("student-courses-picker");
    const selectedCourses = [];
    picker?.querySelectorAll(".add-student-course-cb:checked").forEach((cb) => {
      selectedCourses.push(cb.value);
    });

    const dept =
      document
        .getElementById(
          "student-department-select"
        )
        ?.value.trim() ||
      "AI & Data Science";

    const payload = {
      name:
        document
          .getElementById(
            "student-name-input"
          )
          ?.value.trim(),

      email:
        document
          .getElementById(
            "student-email-input"
          )
          ?.value.trim() ||
        null,

      department: dept,

      track: dept,

      semester: Number(
        document
          .getElementById(
            "student-semester-input"
          )
          ?.value || 1
      ),

      completed_courses: selectedCourses
    };

    try {
      const res =
        await fetch(
          `${API_BASE}/students`,
          {
            method: "POST",
            headers: {
              "Content-Type":
                "application/json"
            },
            body: JSON.stringify(
              payload
            )
          }
        );

      if (!res.ok) {
        let detail =
          "Unable to create student.";

        try {
          detail =
            (await res.json())
              ?.detail ||
            detail;
        } catch {}

        throw new Error(detail);
      }

      const data =
        await res.json();

      const created =
        data.student;

      await loadStudents();

      closeStudentModal();

      showToast(
        `Student ${created.name} (${created.department}) created with ID ${created.id}.`,
        "success"
      );

      await selectStudent(
        created
      );
    } catch (err) {
      console.error(err);

      showToast(
        err?.message ||
          "Unable to create student.",
        "error"
      );
    } finally {
      if (submit) {
        submit.disabled = false;
        submit.textContent =
          "Create Student";
      }
    }
  }

  function closeStudentMenu() {
    document
      .getElementById(
        "user-dropdown-menu"
      )
      ?.classList.add("hidden");

    document
      .getElementById(
        "user-profile-btn"
      )
      ?.setAttribute(
        "aria-expanded",
        "false"
      );
  }

  function closeStudentModal() {
    document
      .getElementById(
        "student-details-modal"
      )
      ?.classList.add("hidden");

    document
      .getElementById(
        "add-student-modal"
      )
      ?.classList.add("hidden");
  }

  function setLoading(
    isLoading
  ) {
    state.loading =
      isLoading;

    document
      .getElementById(
        "course-loading"
      )
      ?.classList.toggle(
        "hidden",
        !isLoading
      );

    document
      .getElementById(
        "course-content"
      )
      ?.classList.toggle(
        "hidden",
        isLoading
      );

    const send =
      document.getElementById(
        "copilot-send-btn"
      );

    if (send)
      send.disabled = false;
  }

  function showCourseError(
    show,
    message = ""
  ) {
    document
      .getElementById(
        "course-error"
      )
      ?.classList.toggle(
        "hidden",
        !show
      );

    if (message) {
      setText(
        "course-error-text",
        message
      );
    }
  }

  async function fetchJson(
    url,
    options = {}
  ) {
    const res = await fetch(
      url,
      {
        cache: "no-store",
        ...options
      }
    );

    if (!res.ok) {
      let detail = "";

      try {
        detail =
          (await res.json())
            ?.detail || "";
      } catch {}

      throw new Error(
        detail ||
          `Request failed: ${res.status}`
      );
    }

    return res.json();
  }

  function closeGraphModal() {
    document
      .getElementById(
        "prerequisite-modal"
      )
      ?.classList.add("hidden");
  }

  function getCourse(code) {
    return state.courses.find(
      (c) =>
        String(
          c.code
        ).toUpperCase() ===
        String(
          code
        ).toUpperCase()
    );
  }

  function emptyInline(
    message
  ) {
    return `
      <div class="col-span-full rounded-lg border border-dashed border-white/10 p-6 text-center text-[10px] text-slate-500">
        ${escapeHtml(
          message
        )}
      </div>
    `;
  }

  function setText(
    id,
    value
  ) {
    const el =
      document.getElementById(id);

    if (el)
      el.textContent = value;
  }

  function escapeHtml(
    value
  ) {
    return String(
      value ?? ""
    ).replace(
      /[&<>"']/g,
      (ch) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#039;"
        }[ch])
    );
  }

  function escapeAttr(
    value
  ) {
    return escapeHtml(value);
  }

  function friendlyError(
    err
  ) {
    const msg =
      err?.message ||
      "Unknown error";

    if (
      msg.includes(
        "Failed to fetch"
      )
    ) {
      return "FastAPI is unreachable. Please check your internet connection and try again.";
    }

    return msg;
  }

  function showToast(
    message,
    type = "info"
  ) {
    let host =
      document.getElementById(
        "toast-host"
      );

    if (!host) {
      host =
        document.createElement(
          "div"
        );

      host.id =
        "toast-host";

      host.className =
        "fixed bottom-5 right-5 z-[120] space-y-2";

      document.body.appendChild(
        host
      );
    }

    const toast =
      document.createElement(
        "div"
      );

    toast.className =
      `rounded-xl border px-4 py-3 text-xs shadow-2xl backdrop-blur-xl ${
        type === "success"
          ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
          : type === "error"
          ? "border-rose-400/25 bg-rose-400/10 text-rose-200"
          : "border-white/10 bg-slate-900/90 text-slate-200"
      }`;

    toast.textContent =
      message;

    host.appendChild(
      toast
    );

    setTimeout(
      () => toast.remove(),
      3500
    );
  }
})();