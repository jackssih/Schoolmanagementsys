(function () {
    let activeReport = null;
    let activeStudentId = null;
    let previewMode = "individual";

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function parseRecord(button) {
        try {
            return JSON.parse(button.dataset.record || "{}");
        } catch (error) {
            console.error("Could not read report data:", error);
            return {};
        }
    }

    function selectedStudent() {
        const students = activeReport?.students || [];
        return students.find((student) => student.id === activeStudentId) || students[0];
    }

    // --- Marks pivot helpers ---
    //
    // student.assessments is a flat list of rows: { subject, type, maximum, mark, aggregate, grade, mode }
    // "type" is the real assessment period: "B.O.T.", "Mid", "E.O.T Internal", or "E.O.T External" — every
    // subject uses these same periods now. "mode" ("marks" vs "letter") is what actually separates Major
    // subjects from Other subjects, driven by each subject's compulsory flag on the backend.

    function numeric(value) {
        if (value === "" || value === null || value === undefined) return null;
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
    }

    // Standard PLE-style aggregate bands. Adjust the cutoffs here if your school uses a different scale.
    function computeDivision(totalAggregate) {
        if (totalAggregate <= 12) return "1";
        if (totalAggregate <= 23) return "2";
        if (totalAggregate <= 29) return "3";
        if (totalAggregate <= 33) return "4";
        return "U";
    }

    function groupMarkRows(student) {
        const groups = {};
        (student.assessments || []).forEach((row) => {
            if (row.mode !== "marks") return;
            if (!groups[row.type]) groups[row.type] = [];
            groups[row.type].push(row);
        });
        return groups;
    }

    function schoolInitials(name) {
        const words = (name || "").trim().split(/\s+/).filter(Boolean);
        if (!words.length) return "S";
        if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
        return (words[0][0] + words[1][0]).toUpperCase();
    }

    function subjectsFromRows(rows) {
        const subjects = [];
        (rows || []).forEach((r) => {
            if (!subjects.includes(r.subject)) subjects.push(r.subject);
        });
        return subjects;
    }

    function rowFor(subject, rows) {
        return (rows || []).find((r) => r.subject === subject);
    }

    // label: "B.O.T." or "Mid". subjects: fixed column list to render (may be wider than what has data).
    // rows: whatever assessment rows exist for this period — subjects with no matching row render blank.
    function renderSimplePeriodTable(label, subjects, rows) {
        if (!subjects || !subjects.length) {
            return `
                <table class="report-period-table">
                    <thead><tr class="period-header-row"><th class="period-label">${escapeHtml(label)}</th><th>No subjects set up yet</th></tr></thead>
                </table>
            `;
        }

        let totalMark = 0, markCount = 0, totalAgg = 0, aggCount = 0;

        const markCells = subjects.map((subject) => {
            const r = rowFor(subject, rows);
            const m = r ? numeric(r.mark) : null;
            if (m !== null) { totalMark += m; markCount += 1; }
            return `<td>${m !== null ? escapeHtml(r.mark) : ""}</td>`;
        }).join("");

        const aggCells = subjects.map((subject) => {
            const r = rowFor(subject, rows);
            const a = r ? numeric(r.aggregate) : null;
            if (a !== null) { totalAgg += a; aggCount += 1; }
            return `<td>${a !== null ? escapeHtml(r.aggregate) : ""}</td>`;
        }).join("");

        const division = aggCount ? computeDivision(totalAgg) : "";

        return `
            <table class="report-period-table">
                <thead>
                    <tr class="period-header-row">
                        <th class="period-label">${escapeHtml(label)}</th>
                        ${subjects.map((s) => `<th>${escapeHtml(s)}</th>`).join("")}
                        <th>Total</th>
                        <th>Division</th>
                    </tr>
                </thead>
                <tbody>
                    <tr class="marks-row">
                        <th>Marks</th>
                        ${markCells}
                        <td>${markCount ? totalMark : ""}</td>
                        <td></td>
                    </tr>
                    <tr class="aggregates-row">
                        <th>Aggregates</th>
                        ${aggCells}
                        <td>${aggCount ? totalAgg : ""}</td>
                        <td>${division}</td>
                    </tr>
                </tbody>
            </table>
        `;
    }

    // subjects: fixed column list. internalRows/externalRows: whatever E.O.T. results exist.
    function renderEotTable(subjects, internalRows, externalRows) {
        internalRows = internalRows || [];
        externalRows = externalRows || [];

        if (!subjects || !subjects.length) {
            return `
                <table class="report-period-table report-eot-table">
                    <thead><tr class="period-header-row"><th class="period-label">E.O.T.</th><th>No subjects set up yet</th></tr></thead>
                </table>
            `;
        }

        function renderRow(label, rows) {
            let totalMark = 0, markCount = 0, totalAgg = 0, aggCount = 0;
            const cells = subjects.map((subject) => {
                const r = rowFor(subject, rows);
                const m = r ? numeric(r.mark) : null;
                const a = r ? numeric(r.aggregate) : null;
                if (m !== null) { totalMark += m; markCount += 1; }
                if (a !== null) { totalAgg += a; aggCount += 1; }
                return `<td>${m !== null ? escapeHtml(r.mark) : ""}</td><td>${a !== null ? escapeHtml(r.aggregate) : ""}</td>`;
            }).join("");
            const division = aggCount ? computeDivision(totalAgg) : "";
            return `
                <tr>
                    <th>${escapeHtml(label)}</th>
                    ${cells}
                    <td>${markCount ? totalMark : ""}</td>
                    <td>${aggCount ? totalAgg : ""}</td>
                    <td>${division}</td>
                </tr>
            `;
        }

        return `
            <table class="report-period-table report-eot-table">
                <thead>
                    <tr class="period-header-row">
                        <th class="period-label">E.O.T.</th>
                        ${subjects.map((s) => `<th colspan="2">${escapeHtml(s)}</th>`).join("")}
                        <th colspan="2">Total</th>
                        <th rowspan="2">Division</th>
                    </tr>
                    <tr class="sub-header-row">
                        <th class="marks-subheader-label">Marks</th>
                        ${subjects.map(() => `<th>MKS</th><th>AGG</th>`).join("")}
                        <th>MKS</th><th>AGG</th>
                    </tr>
                </thead>
                <tbody>
                    ${renderRow("Internal", internalRows)}
                    ${renderRow("External", externalRows)}
                </tbody>
            </table>
        `;
    }

    function otherSubjectRows(student) {
        const rows = (student.assessments || []).filter((row) => row.mode === "letter");
        if (!rows.length) return "";
        return `
            <table class="report-other-subjects-table">
                <thead><tr><th>Other subjects</th><th>Period</th><th>Grade</th><th>Teacher's assessment</th></tr></thead>
                <tbody>
                    ${rows.map((row) => `
                        <tr>
                            <td>${escapeHtml(row.subject)}</td>
                            <td>${escapeHtml(row.type)}</td>
                            <td>${escapeHtml(row.grade || "—")}</td>
                            <td>${escapeHtml(row.remark || "—")}</td>
                        </tr>
                    `).join("")}
                </tbody>
            </table>
        `;
    }

    function renderReportCard(student) {
        const groups = groupMarkRows(student);
        const mainSubjects = student.main_subjects || [];
        const reportType = activeReport.report_type;

        let periodTablesHtml = "";
        if (reportType === "End of term") {
            // End of term always shows all three sections, even with no marks recorded yet —
            // columns come from the class's registered subjects, not from whatever data exists.
            periodTablesHtml += renderSimplePeriodTable("B.O.T.", mainSubjects, groups["B.O.T."]);
            periodTablesHtml += renderSimplePeriodTable("Mid", mainSubjects, groups["Mid"]);
            periodTablesHtml += renderEotTable(mainSubjects, groups["E.O.T Internal"], groups["E.O.T External"]);
        } else if (reportType === "Beginning of term") {
            const rows = groups["B.O.T."] || [];
            periodTablesHtml = rows.length ? renderSimplePeriodTable("B.O.T.", subjectsFromRows(rows), rows) : "";
        } else if (reportType === "Mid-term") {
            const rows = groups["Mid"] || [];
            periodTablesHtml = rows.length ? renderSimplePeriodTable("Mid", subjectsFromRows(rows), rows) : "";
        } else {
            // Fallback for other report kinds (Assessment report, Attendance report): show whatever exists.
            ["B.O.T.", "Mid"].forEach((type) => {
                const rows = groups[type] || [];
                if (rows.length) periodTablesHtml += renderSimplePeriodTable(type, subjectsFromRows(rows), rows);
            });
            if ((groups["E.O.T Internal"] || []).length || (groups["E.O.T External"] || []).length) {
                const eotSubjects = subjectsFromRows([...(groups["E.O.T Internal"] || []), ...(groups["E.O.T External"] || [])]);
                periodTablesHtml += renderEotTable(eotSubjects, groups["E.O.T Internal"], groups["E.O.T External"]);
            }
        }
        if (!periodTablesHtml) {
            periodTablesHtml = '<p class="report-empty-note">No marks recorded for this period yet.</p>';
        }

        const otherSubjectsHtml = otherSubjectRows(student);

        const contactLine1 = [
            SCHOOL_INFO.address,
            SCHOOL_INFO.phone ? `Tel: ${SCHOOL_INFO.phone}` : "",
        ].filter(Boolean).map(escapeHtml).join(" &middot; ");

        const contactLine2 = [
            SCHOOL_INFO.email ? `Email: ${SCHOOL_INFO.email}` : "",
            SCHOOL_INFO.website ? `Website: ${SCHOOL_INFO.website}` : "",
        ].filter(Boolean).map(escapeHtml).join(" &middot; ");

        const crestInner = SCHOOL_INFO.logo_path
            ? `<img src="/static/${SCHOOL_INFO.logo_path}" alt="${escapeHtml(SCHOOL_NAME)} logo">`
            : escapeHtml(schoolInitials(SCHOOL_NAME));

        const watermarkInner = SCHOOL_INFO.logo_path
            ? `<img src="/static/${SCHOOL_INFO.logo_path}" alt="">`
            : `<div class="report-watermark-placeholder"></div>`;

        return `
            <article class="report-card-page">
                <div class="report-card-frame">
                    <div class="report-card-brand">
                        <div>
                            <p class="report-school-name">${escapeHtml(SCHOOL_NAME)}</p>
                            ${SCHOOL_INFO.type ? `<p class="report-school-type">${escapeHtml(SCHOOL_INFO.type)}</p>` : ""}
                        </div>
                        <div class="report-crest">${crestInner}</div>
                    </div>

                    <div class="report-card-title-row">
                        <p class="report-class-term">
                            <span><strong>Class:</strong> <span class="report-highlight">${escapeHtml(student.class_name)}</span></span>
                            <span><strong>Term:</strong> <span class="report-highlight">${escapeHtml(CURRENT_TERM_NAME || "—")}</span></span>
                        </p>
                        <h3>${escapeHtml(reportType)} Report Card</h3>
                    </div>

                    <div class="report-meta-wrap">
                        <div class="report-meta-watermark">${watermarkInner}</div>
                        <table class="report-meta-table">
                            <tr><th>Pupil's name</th><td>${escapeHtml((student.name || "").toUpperCase())}</td></tr>
                            <tr><th>Date of birth</th><td>${escapeHtml(student.date_of_birth || "—")}</td></tr>
                            <tr><th>Date of enrollment</th><td>${escapeHtml(student.enrollment_date || "—")}</td></tr>
                            <tr><th>LIN</th><td>${escapeHtml(student.lin || "")}</td></tr>
                            <tr><th>Class teacher</th><td>${escapeHtml(student.class_teacher || "—")}</td></tr>
                            <tr><th>Date</th><td>${escapeHtml(activeReport.created_at || activeReport.published_at || "—")}</td></tr>
                        </table>
                    </div>

                    <div class="report-grading-scale">
                        <p class="report-grading-scale-title">Grading scale</p>
                        <p>A: Well above the expected standard of the term.</p>
                        <p>B: Above the expected standard of the term.</p>
                        <p>C: At the expected standard of the term.</p>
                        <p>D: Below the expected standard of the term.</p>
                        <p>E: Well below the expected standard of the term.</p>
                    </div>

                    <div class="report-period-tables">${periodTablesHtml}</div>

                    ${otherSubjectsHtml}

                    <div class="report-comments">
                        <p><strong>Class teacher's general comment:</strong> ${escapeHtml(student.comments["Class teacher"] || "—")}</p>
                        <p><strong>Head teacher's comment:</strong> ${escapeHtml(student.comments["Head teacher"] || "—")}</p>
                    </div>

                    <div class="report-card-footer">
                        <div class="report-flag-badge">
                            <div class="report-flag">
                                <span></span><span></span><span></span><span></span><span></span><span></span>
                                <div class="report-flag-circle"></div>
                            </div>
                            <div class="report-flag-text">
                                <strong>UGANDA</strong>
                                <span>National Curriculum</span>
                                ${SCHOOL_INFO.reg_no ? `<span class="report-reg-no">REG No: ${escapeHtml(SCHOOL_INFO.reg_no)}</span>` : ""}
                            </div>
                        </div>
                        ${(contactLine1 || contactLine2) ? `
                            <p class="report-contact-line">
                                ${contactLine1}${contactLine1 && contactLine2 ? "<br>" : ""}${contactLine2}
                            </p>` : ""}
                    </div>
                </div>
            </article>
        `;
    }

    function renderStudentList() {
        const query = document.getElementById("reportStudentSearch").value.toLowerCase();
        const list = document.getElementById("reportStudentList");
        const students = (activeReport.students || []).filter((student) => student.name.toLowerCase().includes(query));
        list.innerHTML = students.length ? students.map((student) => `
            <button type="button" class="report-student-item ${student.id === activeStudentId ? "active" : ""}" data-student-id="${student.id}">
                <i class="ti ti-file-text"></i>
                <span>
                    <strong>${escapeHtml(student.name)}</strong>
                    <small>${escapeHtml(activeReport.created_at || activeReport.published_at)} · Generated</small>
                </span>
            </button>
        `).join("") : '<p class="form-subheading">No students found.</p>';
    }

    function renderPreview() {
        const documentEl = document.getElementById("reportDocument");
        const students = activeReport?.students || [];
        if (!students.length) {
            documentEl.innerHTML = '<p class="form-subheading">No generated reports are available yet.</p>';
            document.getElementById("reportPageCount").textContent = "0 Pages";
            return;
        }
        if (previewMode === "all") {
            documentEl.innerHTML = students.map(renderReportCard).join("");
            document.getElementById("reportPageCount").textContent = `${students.length} Pages`;
        } else {
            documentEl.innerHTML = renderReportCard(selectedStudent());
            document.getElementById("reportPageCount").textContent = "1 Page";
        }
        renderStudentList();
    }

    function openPreview(record) {
        activeReport = record;
        activeStudentId = (record.students && record.students[0] && record.students[0].id) || null;
        previewMode = "individual";
        document.getElementById("reportPreviewTitle").textContent = `${record.class_name} - ${record.report_type}`;
        document.getElementById("reportPreviewSubtitle").textContent = `Generated on: ${record.created_at || record.published_at || "—"}`;
        document.getElementById("reportStudentSearch").value = "";
        document.querySelectorAll(".report-preview-tab").forEach((tab) => {
            tab.classList.toggle("active", tab.dataset.previewMode === "individual");
        });
        document.getElementById("reportPreviewOverlay").classList.add("open");
        renderPreview();
    }

    function openPublish(record) {
        const form = document.getElementById("publishReportForm");
        form.action = `${REPORT_URL_BASE}/${record.id}/publish`;
        form.reset();
        form.querySelector('[name="publish_here"]').checked = true;
        document.getElementById("publish-email-field").hidden = true;
        openModal("publishReportModal");
    }

    function openDeleteConfirm(formId, label) {
        document.getElementById("confirmDeleteText").textContent =
            `This will permanently remove ${label}. This can't be undone.`;
        document.getElementById("confirmDeleteBtn").onclick = function () {
            document.getElementById(formId).submit();
        };
        openModal("confirmDeleteModal");
    }

    document.addEventListener("click", (event) => {
        const actionButton = event.target.closest("[data-report-action]");
        if (actionButton) {
            const action = actionButton.dataset.reportAction;
            if (action === "preview") openPreview(parseRecord(actionButton));
            if (action === "publish") openPublish(parseRecord(actionButton));
            if (action === "delete") openDeleteConfirm(actionButton.dataset.formId, actionButton.dataset.label || "this report");
            return;
        }

        const studentButton = event.target.closest(".report-student-item");
        if (studentButton) {
            activeStudentId = Number(studentButton.dataset.studentId);
            previewMode = "individual";
            document.querySelectorAll(".report-preview-tab").forEach((tab) => {
                tab.classList.toggle("active", tab.dataset.previewMode === "individual");
            });
            renderPreview();
        }
    });

    document.addEventListener("change", (event) => {
        if (event.target.id === "publish-email-toggle") {
            document.getElementById("publish-email-field").hidden = !event.target.checked;
        }
    });

    document.addEventListener("DOMContentLoaded", () => {
        document.getElementById("reportPreviewClose").addEventListener("click", () => {
            document.getElementById("reportPreviewOverlay").classList.remove("open");
        });
        document.getElementById("reportStudentSearch").addEventListener("input", renderStudentList);
        document.querySelectorAll(".report-preview-tab").forEach((tab) => {
            tab.addEventListener("click", () => {
                previewMode = tab.dataset.previewMode;
                document.querySelectorAll(".report-preview-tab").forEach((item) => item.classList.toggle("active", item === tab));
                renderPreview();
            });
        });
        document.getElementById("reportDownloadBtn").addEventListener("click", () => {
            window.print();
        });
    });
})();