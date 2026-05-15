document.addEventListener('htmx:confirm', function(evt) {
    if (!evt.detail.elt.hasAttribute('data-risk-confirm')) return;
    
    const riskStatus = document.body.dataset.riskStatus || 'ok';
    
    if (riskStatus === 'throttled' || riskStatus === 'warning') {
        evt.preventDefault();
        
        const message = evt.detail.elt.getAttribute('data-risk-confirm') || 
                       'This action is flagged as high-risk. Confirm to proceed?';
        
        if (confirm(message)) {
            evt.detail.issueRequest();
        }
    }
});
