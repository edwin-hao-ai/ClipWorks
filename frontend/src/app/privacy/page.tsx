import type { Metadata } from 'next';
import { LegalLayout, LegalSection } from '@/components/layout/LegalLayout';

export const metadata: Metadata = {
  title: '隐私政策',
  description: 'ClipWorks 映工厂隐私政策（草案）',
};

export default function PrivacyPage() {
  return (
    <LegalLayout title="隐私政策" updatedAt="2026 年 7 月">
      <p className="text-sm leading-relaxed text-content-secondary">
        ClipWorks 映工厂（以下简称「我们」）重视您的隐私。本政策说明我们在为您提供
        AI 视频生成与剪辑服务时，如何收集、使用、存储和保护您的信息。
      </p>

      <LegalSection title="1. 我们收集的信息">
        <ul>
          <li>
            <strong>账号信息</strong>：通过第三方 OAuth 登录时获得的邮箱、昵称与头像
            （当前演示环境为模拟登录，仅保存演示账号信息）。
          </li>
          <li>
            <strong>项目内容</strong>：您创建的项目、输入的文字需求（prompt）、上传的素材文件、
            生成的时间线与成片。
          </li>
          <li>
            <strong>使用数据</strong>：功能使用日志与错误日志，用于排查问题和改进产品。
          </li>
        </ul>
      </LegalSection>

      <LegalSection title="2. 我们如何使用这些信息">
        <ul>
          <li>提供、维护和改进视频生成与剪辑服务；</li>
          <li>将您的文字需求与项目上下文发送给大语言模型（LLM）服务以生成视频方案；</li>
          <li>根据您的素材需求从第三方图库检索配图；</li>
          <li>分析聚合后的使用数据以改进产品体验（不含可识别个人身份的内容）。</li>
        </ul>
      </LegalSection>

      <LegalSection title="3. Cookie 与本地存储">
        <p>
          我们使用会话 Cookie（<code>session_user_id</code>）维持登录状态，使用浏览器
          localStorage 保存主题、通知等界面偏好。这些信息不会用于广告追踪。
        </p>
      </LegalSection>

      <LegalSection title="4. 第三方服务">
        <p>为提供完整功能，我们会调用以下类别的第三方服务：</p>
        <ul>
          <li>大语言模型 API（视频脚本规划与对话修改）；</li>
          <li>在线图库（按主题检索配图，未配置密钥时使用占位图服务）；</li>
          <li>在线语音合成服务（旁白配音，未配置时降级为本地合成）。</li>
        </ul>
        <p>
          这些服务仅接收完成对应功能所必需的数据（如您的 prompt 文本），
          正式版本将在本政策中列出具体服务商名单。
        </p>
      </LegalSection>

      <LegalSection title="5. 数据的存储与安全">
        <p>
          您的项目数据与素材文件存储在我们的服务器上，访问受登录会话保护。
          我们采取合理的工程措施保护数据安全，但请注意：演示环境不构成生产级安全保障，
          请勿上传包含敏感个人信息的素材。
        </p>
      </LegalSection>

      <LegalSection title="6. 您的权利">
        <ul>
          <li>在素材库与项目列表中删除您上传的素材和创建的项目；</li>
          <li>在设置页修改您的昵称与界面偏好；</li>
          <li>联系我们以导出或删除您的账号数据（联系方式见文末）。</li>
        </ul>
      </LegalSection>

      <LegalSection title="7. 未成年人">
        <p>
          本服务面向成年用户。如您是未成年人，请在监护人同意和指导下使用本服务。
        </p>
      </LegalSection>

      <LegalSection title="8. 本政策的更新">
        <p>
          我们可能不定期更新本政策。重大变更将通过站内通知告知您，
          更新后的政策自公布之日起生效。
        </p>
      </LegalSection>

      <LegalSection title="9. 联系我们">
        <p>
          本草案暂未配置对外联系方式。正式版本将在此提供隐私事务联系邮箱，
          您也可以通过产品内的反馈渠道向我们提出隐私相关的请求。
        </p>
      </LegalSection>
    </LegalLayout>
  );
}
