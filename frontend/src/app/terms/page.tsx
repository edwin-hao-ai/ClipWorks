import type { Metadata } from 'next';
import { LegalLayout, LegalSection } from '@/components/layout/LegalLayout';

export const metadata: Metadata = {
  title: '服务条款',
  description: 'ClipWorks 映工厂服务条款（草案）',
};

export default function TermsPage() {
  return (
    <LegalLayout title="服务条款" updatedAt="2026 年 7 月">
      <p className="text-sm leading-relaxed text-content-secondary">
        欢迎使用 ClipWorks 映工厂（以下简称「本服务」）。使用本服务即表示您已阅读、
        理解并同意接受本条款的全部内容。如您不同意，请停止使用本服务。
      </p>

      <LegalSection title="1. 服务说明">
        <p>
          本服务是一款 AI 驱动的视频生成与剪辑工具：您输入文字需求或素材，
          系统自动规划视频脚本、合成时间线并渲染输出视频。
        </p>
        <p>
          <strong>本服务目前处于演示/MVP 阶段</strong>，功能、性能与可用性均按「现状」提供，
          我们可能随时调整、暂停或终止部分功能，恕不另行通知。
        </p>
      </LegalSection>

      <LegalSection title="2. 账号与登录">
        <p>
          演示环境使用模拟 OAuth 登录，仅用于体验产品流程，不代表真实的身份认证。
          正式版本上线后，您需要使用真实账号重新注册，演示数据不保证迁移。
        </p>
      </LegalSection>

      <LegalSection title="3. 额度与计费">
        <ul>
          <li>演示环境不涉及任何真实支付；页面展示的套餐与价格均为演示用途；</li>
          <li>生成额度（credits）用于限制演示环境的资源消耗，切换套餐会按演示规则补足额度；</li>
          <li>正式版本将推出真实的计费方案，届时以届时公布的条款为准。</li>
        </ul>
      </LegalSection>

      <LegalSection title="4. 您的内容与责任">
        <ul>
          <li>您保留对上传素材及输入内容的全部权利；</li>
          <li>
            您保证拥有所上传素材的合法使用权，不上传侵犯他人知识产权、肖像权，
            或包含违法、敏感信息的内容；
          </li>
          <li>
            您授予我们一项有限的、非独占的许可，仅为向您提供本服务之目的
            存储、处理和渲染您的内容；
          </li>
          <li>因您上传的内容引发的任何纠纷或索赔，由您自行承担责任。</li>
        </ul>
      </LegalSection>

      <LegalSection title="5. AI 生成内容的声明">
        <ul>
          <li>
            本服务生成的脚本、旁白、配图与视频由 AI 自动生成，
            我们不保证其准确性、完整性或适用于任何特定用途；
          </li>
          <li>AI 生成内容可能包含事实错误或不当表述，发布前请您自行审核；</li>
          <li>
            自动检索的配图来自第三方图库，其授权条款以对应图库网站为准，
            商用前请您自行确认授权范围。
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="6. 知识产权">
        <p>
          本服务的软件、界面设计、商标及相关文档的知识产权归我们所有。
          未经书面许可，您不得复制、修改、反向工程或转售本服务的任何部分。
        </p>
      </LegalSection>

      <LegalSection title="7. 免责声明">
        <p>
          在适用法律允许的最大范围内，本服务按「现状」和「可用」基础提供，
          我们不作任何明示或暗示的保证，包括但不限于适销性、特定用途适用性及不侵权。
          对于因使用或无法使用本服务造成的任何间接、附带或后果性损失，我们不承担责任。
        </p>
      </LegalSection>

      <LegalSection title="8. 服务的变更与终止">
        <p>
          我们可能随时修改、暂停或终止本服务的全部或部分功能。
          如您违反本条款，我们有权限制或终止您对服务的访问。
          您可以随时停止使用本服务并删除您的项目数据。
        </p>
      </LegalSection>

      <LegalSection title="9. 适用法律与争议解决">
        <p>
          本草案暂未约定适用法律与争议解决方式，正式版本将在此补充完整条款。
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
