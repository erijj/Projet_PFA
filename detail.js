function copyHash(){navigator.clipboard.writeText(document.getElementById('tx-hash').textContent).then(()=>showToast('Hash copié !'));}
function shareLink(){
  const url=window.location.href;
  if(navigator.share)navigator.share({title:'Mon certificat SmartCert',url});
  else navigator.clipboard.writeText(url).then(()=>showToast('Lien copié !'));
}
function showToast(msg){const t=document.getElementById('toast');document.getElementById('toast-msg').textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3000);}