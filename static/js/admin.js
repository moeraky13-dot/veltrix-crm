/* ===== VELTRIX CRM — Admin JS ===== */

// تأكيد الحذف
document.addEventListener('DOMContentLoaded', function() {
    // تحديث نص روابط الإجراءات
    document.querySelectorAll('[data-confirm]').forEach(function(el) {
        el.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) e.preventDefault();
        });
    });
});
