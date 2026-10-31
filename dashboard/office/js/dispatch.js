import { WHO, roomById } from './constants.js';

const esc = s =>
  String(s ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));

// Define tailored task templates per staff member
export function getTasksForStaff(staff) {
  switch (staff.id) {
    case 'owner':
      return [
        {
          key: 'new_video',
          tabLabel: 'Tạo video mới',
          btnLabel: 'Khởi tạo thư mục video',
          needsVideo: false,
          fields: [
            {
              name: 'topic',
              label: 'Chủ đề hoặc cụm từ tìm kiếm (tiếng Anh)',
              type: 'text',
              placeholder: 'how ancient humans survived ice age winters',
              helper: 'Tạo thư mục video mới theo mẫu chuẩn trong kênh hiện tại.',
              required: true,
            },
          ],
        },
      ];

    case 'assistant':
      return [
        {
          key: 'claude',
          tabLabel: 'Giao việc cho Claude',
          btnLabel: 'Gửi yêu cầu cho Claude',
          needsVideo: true,
          fields: [
            {
              name: 'message',
              label: 'Nội dung yêu cầu (tiếng Việt)',
              type: 'textarea',
              placeholder: 'Kiểm tra lại các con số trong kịch bản với bảng sources_log.csv...',
              helper: 'Claude chạy trực tiếp trong thư mục video được chọn.',
              required: true,
            },
            {
              name: 'model',
              label: 'Mô hình Claude',
              type: 'select',
              options: [
                { value: 'sonnet', label: 'Claude Sonnet (Mặc định)' },
                { value: 'opus', label: 'Claude Opus (Sâu nhất)' },
                { value: 'haiku', label: 'Claude Haiku (Nhanh)' },
              ],
            },
          ],
        },
        {
          key: 'gemini',
          tabLabel: 'Hỏi nhanh Gemini',
          btnLabel: 'Gửi yêu cầu cho Gemini',
          needsVideo: true,
          fields: [
            {
              name: 'message',
              label: 'Câu hỏi hoặc yêu cầu nghiên cứu',
              type: 'textarea',
              placeholder: 'Tìm thêm 5 bằng chứng khảo cổ học có nguồn URL uy tín cho chủ đề này...',
              helper: 'Gemini (agy) sẽ tra cứu và lưu bản nháp vào research/gemini/.',
              required: true,
            },
          ],
        },
      ];

    case 'researcher':
      return [
        {
          key: 'research_topic',
          tabLabel: 'Nghiên cứu chủ đề',
          btnLabel: 'Chạy nghiên cứu chủ đề',
          needsVideo: true,
          allowChannelLevel: true,
          fields: [
            {
              name: 'query',
              label: 'Cụm từ tìm kiếm YouTube (tiếng Anh)',
              type: 'text',
              placeholder: 'how ancient humans survived without medicine',
              helper: 'Tìm câu hỏi khán giả, 8-12 dữ kiện có URL nguồn gốc và 3 góc tiếp cận mới.',
              required: true,
            },
          ],
        },
        {
          key: 'suggest_phrases',
          tabLabel: 'Gợi ý cụm từ mới',
          btnLabel: 'Gợi ý cụm từ tìm kiếm',
          needsVideo: false,
          fields: [
            {
              name: 'n',
              label: 'Số lượng cụm từ cần gợi ý',
              type: 'number',
              value: '15',
              helper: 'Mặc định 15 cụm từ tiếng Anh khán giả Mỹ thường gõ.',
            },
            {
              name: 'hint',
              label: 'Gợi ý ngách hoặc hướng chủ đề (tùy chọn)',
              type: 'text',
              placeholder: 'Ví dụ: tập trung vào y học cổ đại, thức ăn thời tiền sử...',
              helper: 'Để trống nếu muốn mở rộng toàn kênh.',
            },
          ],
        },
        {
          key: 'competitors',
          tabLabel: 'Phân tích đối thủ',
          btnLabel: 'Chạy phân tích đối thủ',
          needsVideo: true,
          fields: [
            {
              name: 'query',
              label: 'Cụm từ tìm kiếm hoặc danh sách URL video đối thủ',
              type: 'textarea',
              placeholder: 'how prehistoric humans survived',
              helper: 'Phân tích cấu trúc, hook 30 giây đầu và điểm mạnh/yếu từ bình luận.',
              required: true,
            },
          ],
        },
      ];

    case 'scout':
      return [
        {
          key: 'scout',
          tabLabel: 'Đo cụm từ (yt-dlp)',
          btnLabel: 'Bắt đầu đo dữ liệu YouTube',
          needsVideo: false,
          fields: [
            {
              name: 'phrases',
              label: 'Danh sách cụm từ tìm kiếm tiếng Anh (mỗi dòng 1 cụm từ)',
              type: 'textarea',
              placeholder: 'how ancient humans survived winter\nhow cavemen treated broken bones\ndaily life in mesolithic',
              helper: 'Chạy scout.py đo lượt xem, độ mới và kênh nhỏ thắng cuộc.',
              required: true,
            },
          ],
        },
      ];

    case 'writer':
      return [
        {
          key: 'write_script',
          tabLabel: 'Viết kịch bản mới',
          btnLabel: 'Giao Claude viết kịch bản',
          needsVideo: true,
          fields: [],
          info: 'Đọc research/topic.md và các bản nháp trong research/gemini/, kiểm chứng URL nguồn, viết script/script.txt và lập bảng research/sources_log.csv.',
        },
        {
          key: 'fix_script',
          tabLabel: 'Sửa theo góp ý Sim',
          btnLabel: 'Áp dụng góp ý người xem thử',
          needsVideo: true,
          fields: [],
          info: 'Đọc biên bản giả lập người xem mới nhất (*_simulate.md) và tinh chỉnh script/script.txt mà không thêm dữ kiện thiếu nguồn.',
        },
        {
          key: 'claude',
          tabLabel: 'Yêu cầu chỉnh kịch bản',
          btnLabel: 'Gửi yêu cầu cho Biên kịch',
          needsVideo: true,
          fields: [
            {
              name: 'message',
              label: 'Ghi chú chỉnh sửa kịch bản',
              type: 'textarea',
              placeholder: 'Rút gọn đoạn mở đầu 01 dưới 45 từ và làm rõ câu hỏi mở...',
              required: true,
            },
          ],
        },
      ];

    case 'viewer':
      return [
        {
          key: 'simulate',
          tabLabel: 'Giả lập người xem (1 lượt)',
          btnLabel: 'Chạy giả lập người xem',
          needsVideo: true,
          fields: [],
          info: 'Đọc script/script.txt theo sim-protocol.md để chỉ ra đoạn dễ rời bỏ, câu khó hiểu và gợi ý viết lại từng đoạn.',
        },
      ];

    case 'director':
      return [
        {
          key: 'make_shots',
          tabLabel: 'Chia cảnh & nhân vật',
          btnLabel: 'Tạo cast.json, shots.json & prompt',
          needsVideo: true,
          fields: [],
          info: 'Tự động chia kịch bản thành danh sách nhân vật (cast.json), cảnh quay (shots.json) và chạy make_prompts.py đến khi đạt 0 lỗi.',
        },
        {
          key: 'claude_shot',
          tabLabel: 'Viết lại 1 cảnh',
          btnLabel: 'Giao sửa prompt cảnh này',
          needsVideo: true,
          fields: [
            {
              name: 'id',
              label: 'Mã cảnh cần sửa (ví dụ: 01-02)',
              type: 'text',
              placeholder: '01-02',
              required: true,
            },
            {
              name: 'note',
              label: 'Mô tả lỗi cần tránh hoặc nội dung muốn đổi',
              type: 'textarea',
              placeholder: 'Tay nhân vật bị tô trắng, cần đổi tư thế đứng cầm ngọn giáo rõ ràng hơn...',
              helper: 'Claude sẽ viết lại cảnh trong shots.json để tránh lỗi và tạo lại prompt.',
              required: true,
            },
          ],
        },
      ];

    case 'checker':
      return [
        {
          key: 'check_prompts',
          tabLabel: 'Kiểm định Prompt',
          btnLabel: 'Chạy kiểm tra chuẩn style',
          needsVideo: true,
          fields: [],
          info: 'Chạy make_prompts.py --check để xác thực toàn bộ giới hạn nhân vật, tư thế, từ cấm và độ dài prompt.',
        },
        {
          key: 'prompts',
          tabLabel: 'Tạo lại bộ Prompt',
          btnLabel: 'Sinh lại toàn bộ file Prompt',
          needsVideo: true,
          fields: [],
          info: 'Đọc cast.json và shots.json để xuất lại toàn bộ file trong images/prompts/.',
        },
      ];

    case 'p1':
    case 'p2':
    case 'p3':
    case 'p4':
      return [
        {
          key: 'generate',
          tabLabel: 'Vẽ ảnh cảnh (Gemini)',
          btnLabel: 'Bắt đầu vẽ ảnh cảnh',
          needsVideo: true,
          fields: [
            {
              name: 'workers',
              label: 'Số họa sĩ vẽ song song (Workers)',
              type: 'select',
              options: [
                { value: '4', label: '4 họa sĩ cùng vẽ (Nhanh nhất)' },
                { value: '3', label: '3 họa sĩ cùng vẽ' },
                { value: '2', label: '2 họa sĩ cùng vẽ' },
                { value: '1', label: '1 họa sĩ vẽ tuần tự' },
              ],
              value: String(staff.painter || 4),
            },
            {
              name: 'only',
              label: 'Chỉ vẽ các mã cảnh cụ thể (tùy chọn, cách nhau dấu phẩy)',
              type: 'text',
              placeholder: 'Để trống để vẽ mọi cảnh còn thiếu (ví dụ: 01-02,02-03)',
            },
            {
              name: 'limit',
              label: 'Giới hạn số lượng ảnh tối đa trong lượt này (tùy chọn)',
              type: 'number',
              placeholder: 'Ví dụ: 10 (để trống là không giới hạn)',
            },
          ],
        },
        {
          key: 'redo',
          tabLabel: 'Vẽ lại 1 ảnh',
          btnLabel: 'Tạo lại ảnh cảnh này',
          needsVideo: true,
          fields: [
            {
              name: 'id',
              label: 'Mã ảnh cảnh cần vẽ lại',
              type: 'text',
              placeholder: '01-02',
              helper: 'Tự động đính kèm ghi chú sửa lỗi từ review.json (nếu có).',
              required: true,
            },
          ],
        },
      ];

    case 'reviewer':
      return [
        {
          key: 'review',
          tabLabel: 'Kiểm duyệt ảnh (QA)',
          btnLabel: 'Chạy Gemini kiểm duyệt ảnh',
          needsVideo: true,
          fields: [
            {
              name: 'only',
              label: 'Chỉ kiểm các mã cảnh cụ thể (tùy chọn, cách nhau dấu phẩy)',
              type: 'text',
              placeholder: 'Để trống để kiểm toàn bộ ảnh mới',
              helper: 'Đối chiếu từng ảnh cảnh với Cast Sheet và chấm điểm 1-5 vào review.json.',
            },
          ],
        },
      ];

    case 'voicebot':
      return [
        {
          key: 'voice_text',
          tabLabel: 'Tách văn bản TTS',
          btnLabel: 'Tạo các file voiceover_tts/NN.txt',
          needsVideo: true,
          fields: [],
          info: 'Loại bỏ thẻ [src: ...], áp dụng từ điển phát âm pronounce.json và tách từng đoạn cho công cụ ElevenLabs.',
        },
        {
          key: 'import_tts',
          tabLabel: 'Nhập MP3 từ Downloads',
          btnLabel: 'Chép file MP3 vào thư mục audio/',
          needsVideo: true,
          fields: [],
          extraPayload: { apply: true },
          info: 'Tự động tìm các file NN.mp3 mới tạo trong ~/Downloads/tts và chép vào thư mục audio/ của video.',
        },
        {
          key: 'open_tts',
          tabLabel: 'Mở thư mục TTS',
          btnLabel: 'Mở trong Finder',
          needsVideo: true,
          fields: [],
          info: 'Mở nhanh thư mục script/voiceover_tts trên Finder.',
        },
      ];

    case 'render':
      return [
        {
          key: 'render',
          tabLabel: 'Kết xuất Video 1440p',
          btnLabel: 'Bắt đầu dựng MP4 1440p',
          needsVideo: true,
          fields: [],
          info: 'Ghép các khung hình 2560x1440, file thu âm MP3, hiệu ứng chuyển cảnh Ken Burns và phụ đề SRT thành bản MP4 1440p hoàn chỉnh.',
        },
        {
          key: 'studio',
          tabLabel: 'Mở Remotion Studio',
          btnLabel: 'Khởi chạy Remotion Studio',
          needsVideo: true,
          fields: [],
          info: 'Mở giao diện xem trước trực tiếp trên trình duyệt để tinh chỉnh nhịp hình.',
        },
      ];

    case 'publisher':
      return [
        {
          key: 'write_upload',
          tabLabel: 'Soạn hồ sơ đăng tải',
          btnLabel: 'Viết file upload/upload.txt',
          needsVideo: true,
          fields: [],
          info: 'Soạn tiêu đề chuẩn yt-packaging, phần mô tả kèm danh sách chương mục từ SRT, dòng trích dẫn nguồn ngắn gọn và bộ thẻ tag.',
        },
      ];

    case 'marketer':
      return [
        {
          key: 'titles',
          tabLabel: 'Nháp Tiêu đề & Ý tưởng',
          btnLabel: 'Tạo 10 tiêu đề & 5 ý tưởng Thumbnail',
          needsVideo: true,
          fields: [],
          info: 'Đọc kịch bản và hồ sơ nhân vật để đề xuất 10 phương án tiêu đề (< 60 ký tự), 5 bố cục thumbnail và 15 thẻ tag.',
        },
        {
          key: 'thumb',
          tabLabel: 'Vẽ Thumbnail 1280x720',
          btnLabel: 'Tạo ảnh Thumbnail',
          needsVideo: true,
          fields: [
            {
              name: 'concept',
              label: 'Mô tả cảnh trong Thumbnail (tiếng Anh)',
              type: 'textarea',
              placeholder: 'The prehistoric elder sitting by a cave fire holding a healed femur bone, dramatic contrast',
              helper: 'Gemini sẽ vẽ nền minh họa không chữ, sau đó code tự động vẽ chữ lớn chuẩn xác.',
              required: true,
            },
            {
              name: 'text',
              label: 'Chữ lớn in trên Thumbnail (tiếng Anh, tối đa 3-4 từ)',
              type: 'text',
              placeholder: 'FIRST EVIDENCE',
            },
          ],
        },
      ];

    default:
      return [];
  }
}

export function setupDispatchModal({ getState, getChannel, onDispatched }) {
  const backdrop = document.querySelector('#dispatch-backdrop');
  const core = document.querySelector('#dispatch-core');
  let activeStaff = null;
  let activeTabIdx = 0;

  function close() {
    backdrop.classList.add('hidden');
    activeStaff = null;
  }

  backdrop.addEventListener('click', e => {
    if (e.target === backdrop) close();
  });

  window.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !backdrop.classList.contains('hidden')) {
      close();
    }
  });

  function open(staff, preferredVideoSlug = null) {
    activeStaff = staff;
    activeTabIdx = 0;
    render(preferredVideoSlug);
    backdrop.classList.remove('hidden');
  }

  function render(preferredVideoSlug = null) {
    if (!activeStaff) return;
    const tasks = getTasksForStaff(activeStaff);
    const task = tasks[activeTabIdx] || tasks[0];
    const st = getState();
    const cid = getChannel();
    const chObj = (st?.channels || []).find(c => c.id === cid);
    const videos = (chObj?.list || []).filter(v => !v.published);
    const defaultSlug =
      preferredVideoSlug ||
      (videos.find(v => v.slug.startsWith('001')) || videos[0])?.slug ||
      '';
    const room = roomById[activeStaff.room];

    core.innerHTML = `
      <div class="modal-head">
        <div class="modal-title-wrap">
          <h2 id="dispatch-title">
            <span class="role-swatch" style="width:11px;height:11px;background:var(--${esc(
              activeStaff.who
            )})"></span>
            <span>Giao việc: ${esc(activeStaff.plaque)}</span>
          </h2>
          <div class="modal-sub">${esc(WHO[activeStaff.who])} · ${esc(room.name)} · ${esc(
      activeStaff.role
    )}</div>
        </div>
        <button type="button" id="dispatch-close">Đóng</button>
      </div>

      ${
        tasks.length > 1
          ? `<div class="task-tabs">
              ${tasks
                .map(
                  (t, idx) =>
                    `<button type="button" class="task-tab ${
                      idx === activeTabIdx ? 'active' : ''
                    }" data-tab="${idx}">${esc(t.tabLabel)}</button>`
                )
                .join('')}
            </div>`
          : ''
      }

      <form id="dispatch-form" class="form-stack">
        ${
          task.needsVideo
            ? `<div class="form-field">
                <label for="f-slug">Hồ sơ Video áp dụng</label>
                <select id="f-slug" name="slug" ${task.allowChannelLevel ? '' : 'required'}>
                  ${
                    task.allowChannelLevel
                      ? '<option value="">Nghiên cứu chung cho toàn kênh</option>'
                      : ''
                  }
                  ${videos
                    .map(
                      v =>
                        `<option value="${esc(v.slug)}" ${
                          v.slug === defaultSlug ? 'selected' : ''
                        }>${esc(v.slug)} - ${esc(v.title)}</option>`
                    )
                    .join('')}
                </select>
                <div class="helper">Kênh hiện tại: ${esc(chObj?.name || cid)}</div>
              </div>`
            : ''
        }

        ${
          task.info
            ? `<div class="stat-card small" style="line-height:1.5">${esc(task.info)}</div>`
            : ''
        }

        ${(task.fields || [])
          .map(f => {
            const id = `f-${f.name}`;
            let inputHtml = '';
            if (f.type === 'textarea') {
              inputHtml = `<textarea id="${id}" name="${esc(f.name)}" placeholder="${esc(
                f.placeholder || ''
              )}" ${f.required ? 'required' : ''}>${esc(f.value || '')}</textarea>`;
            } else if (f.type === 'select') {
              inputHtml = `<select id="${id}" name="${esc(f.name)}">
                ${(f.options || [])
                  .map(
                    o =>
                      `<option value="${esc(o.value)}" ${
                        o.value === f.value ? 'selected' : ''
                      }>${esc(o.label)}</option>`
                  )
                  .join('')}
              </select>`;
            } else {
              inputHtml = `<input id="${id}" type="${esc(f.type || 'text')}" name="${esc(
                f.name
              )}" value="${esc(f.value || '')}" placeholder="${esc(f.placeholder || '')}" ${
                f.required ? 'required' : ''
              }>`;
            }
            return `<div class="form-field">
              <label for="${id}">${esc(f.label)}</label>
              ${inputHtml}
              ${f.helper ? `<div class="helper">${esc(f.helper)}</div>` : ''}
            </div>`;
          })
          .join('')}

        <div class="modal-foot">
          <div id="dispatch-status" class="dispatch-msg"></div>
          <div class="row">
            <button type="button" id="dispatch-cancel">Hủy</button>
            <button type="submit" class="pri" id="dispatch-submit">${esc(
              task.btnLabel
            )} <span class="btn-trail">↗</span></button>
          </div>
        </div>
      </form>
    `;

    core.querySelector('#dispatch-close')?.addEventListener('click', close);
    core.querySelector('#dispatch-cancel')?.addEventListener('click', close);
    core.querySelectorAll('[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTabIdx = Number(btn.dataset.tab);
        render(core.querySelector('#f-slug')?.value || preferredVideoSlug);
      });
    });

    const firstInput = core.querySelector('textarea, input[type="text"]');
    if (firstInput) setTimeout(() => firstInput.focus(), 40);

    const form = core.querySelector('#dispatch-form');
    form?.addEventListener('submit', async e => {
      e.preventDefault();
      const submitBtn = core.querySelector('#dispatch-submit');
      const statusEl = core.querySelector('#dispatch-status');
      submitBtn.disabled = true;
      statusEl.className = 'dispatch-msg';
      statusEl.textContent = 'Đang gửi lệnh...';

      const fd = new FormData(form);
      const payload = {
        action: task.key,
        channel: getChannel(),
        ...(task.extraPayload || {}),
      };

      const slugVal = fd.get('slug');
      if (slugVal) payload.slug = String(slugVal).trim();

      for (const f of task.fields || []) {
        const rawVal = String(fd.get(f.name) ?? '').trim();
        if (!rawVal) continue;
        if (f.name === 'only') {
          payload.only = rawVal
            .split(',')
            .map(s => s.trim())
            .filter(Boolean);
        } else if (f.type === 'number') {
          payload[f.name] = Number(rawVal);
        } else {
          payload[f.name] = rawVal;
        }
      }

      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok || data.error || data.ok === false) {
          statusEl.className = 'dispatch-msg err';
          statusEl.textContent = data.error || data.out || 'Không thể khởi chạy tác vụ';
          submitBtn.disabled = false;
          return;
        }

        statusEl.className = 'dispatch-msg';
        statusEl.textContent = data.out || `Đã giao việc: ${ data.label || task.tabLabel }`;
        if (onDispatched) onDispatched(activeStaff, data);
        setTimeout(() => close(), 650);
      } catch (err) {
        statusEl.className = 'dispatch-msg err';
        statusEl.textContent = 'Lỗi kết nối tới server';
        submitBtn.disabled = false;
      }
    });
  }

  return { open, close };
}
