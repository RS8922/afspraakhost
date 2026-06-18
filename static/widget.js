(function(){
  var key = (document.currentScript || (function(){
    var s = document.getElementsByTagName('script');
    return s[s.length-1];
  })()).src.split('key=')[1];
  if(!key) return;

  var base = (document.currentScript || (function(){
    var s = document.getElementsByTagName('script'); return s[s.length-1];
  })()).src.split('/widget.js')[0];

  // Inject styles
  var style = document.createElement('style');
  style.textContent = `
    #ah-btn{position:fixed;bottom:24px;right:24px;background:linear-gradient(135deg,#10b981,#059669);
      color:#fff;border:none;padding:14px 22px;border-radius:50px;font-size:15px;font-weight:700;
      cursor:pointer;box-shadow:0 4px 20px rgba(16,185,129,.4);z-index:99998;font-family:'Segoe UI',sans-serif;
      display:flex;align-items:center;gap:8px;transition:transform .2s}
    #ah-btn:hover{transform:translateY(-2px)}
    #ah-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:99999;
      align-items:center;justify-content:center}
    #ah-overlay.show{display:flex}
    #ah-frame{width:100%;max-width:440px;height:85vh;max-height:700px;border:none;border-radius:20px;
      box-shadow:0 20px 60px rgba(0,0,0,.5)}
    #ah-close{position:absolute;top:16px;right:16px;background:rgba(255,255,255,.15);border:none;
      color:#fff;width:36px;height:36px;border-radius:50%;font-size:20px;cursor:pointer;
      display:flex;align-items:center;justify-content:center}
  `;
  document.head.appendChild(style);

  // Button
  var btn = document.createElement('button');
  btn.id = 'ah-btn';
  btn.innerHTML = '📅 Afspraak maken';
  document.body.appendChild(btn);

  // Overlay + iframe
  var overlay = document.createElement('div');
  overlay.id = 'ah-overlay';
  var close = document.createElement('button');
  close.id = 'ah-close'; close.textContent = '×';
  var iframe = document.createElement('iframe');
  iframe.id = 'ah-frame';
  iframe.src = base + '/book?key=' + key;
  overlay.appendChild(close);
  overlay.appendChild(iframe);
  document.body.appendChild(overlay);

  btn.addEventListener('click', function(){ overlay.classList.add('show'); });
  close.addEventListener('click', function(){ overlay.classList.remove('show'); });
  overlay.addEventListener('click', function(e){ if(e.target===overlay) overlay.classList.remove('show'); });
})();
